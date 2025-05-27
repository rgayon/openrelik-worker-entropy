import math

from openrelik_worker_common.reporting import Report
from openrelik_worker_common.file_utils import create_output_file
from openrelik_worker_common.task_utils import create_task_result, get_input_files

from .app import celery

# Task name used to register and route the task to the correct queue.
TASK_NAME = "openrelik-worker-entropy.tasks.entropy"

# Task metadata for registration in the core system.
TASK_METADATA = {
    "display_name": "openrelik-worker-entropy",
    "description": "Calculate entropy of files",
    # Configuration that will be rendered as a web for in the UI, and any data entered
    # by the user will be available to the task function when executing (task_config).
    "task_config": [
    ],
}

HIGH_ENTROPY_THRESHOLD = 7.0

def calculate_entropy(data):
    """Calculate entropy of data, as a number of bits of entropy per byte.

    """
    entropy = 0
    if not data:
        return 0
    for x in range(256):
        p_x = float(data.count(x)) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy


@celery.task(bind=True, name=TASK_NAME, metadata=TASK_METADATA)
def run_entropy_task(
    self,
    pipe_result: str = None,
    input_files: list = None,
    output_path: str = None,
    workflow_id: str = None,
    task_config: dict = None,
) -> str:
    """Run Entropy task on input files.

    Args:
        pipe_result: Base64-encoded result from the previous Celery task, if any.
        input_files: List of input file dictionaries (unused if pipe_result exists).
        output_path: Path to the output directory.
        workflow_id: ID of the workflow.
        task_config: User configuration for the task.

    Returns:
        Base64-encoded dictionary containing task results.
    """
    input_files = get_input_files(pipe_result, input_files or [])

    high_entropy_files = []

    for input_file in input_files:
        # Run the command
        with open(input_file.get('path'), "rb") as fh:
            entropy = calculate_entropy(fh.read())
            if entropy >= HIGH_ENTROPY_THRESHOLD:
                filename = input_file.get("display_name")
                high_entropy_files.append([filename, entropy])

    task_report = Report("Entropy analyzer report")

    results_summary = (
            f"Found {len(high_entropy_files)} files "
            f"with high entropy (>{HIGH_ENTROPY_THRESHOLD})."
    )
    summary_section = task_report.add_section()

    result_markdown = "# Files with high entropy"
    result_markdown = '\n'.join(
            [ f" * {path}: {entropy}" for path, entropy in high_entropy_files ])

    summary_section.add_paragraph(results_summary)

    output_file = create_output_file(
            output_path,
            display_name="entropy_results",
            extension=".md",
            data_type="openrelik:entropy:report",
        )
    with open(output_file.path, "w") as outfile:
            outfile.write(result_markdown)

    return create_task_result(
        output_files=[output_file.to_dict()],
        workflow_id=workflow_id,
        meta={},
    )
