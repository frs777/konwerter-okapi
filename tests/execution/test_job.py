from execution.job import JobCoordinator, JobState


def test_one_document_operation_has_one_active_job():
    coordinator = JobCoordinator()

    first = coordinator.create("doc-1", "translate")

    assert first.state is JobState.CREATED
    assert coordinator.create("doc-1", "translate") is first


def test_finished_job_allows_a_new_operation():
    coordinator = JobCoordinator()
    first = coordinator.create("doc-1", "translate")
    coordinator.transition(first.job_id, JobState.COMPLETED)

    second = coordinator.create("doc-1", "translate")

    assert second.job_id != first.job_id
