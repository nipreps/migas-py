import concurrent.futures
from migas.api.operations import CheckProject, GetUsage


def test_check_project_query():
    params = {
        'project': 'owner/repo',
        'project_version': '1.0.0',
        'language': 'python',
        'is_ci': True,
    }
    query = CheckProject._construct_query(params)
    assert 'query' in query
    assert 'check_project' in query
    assert 'project:"owner/repo"' in query
    assert 'project_version:"1.0.0"' in query
    assert 'language:"python"' in query
    assert 'is_ci:true' in query
    # Check selections
    assert 'success,flagged,latest,message' in query


def test_get_usage_query():
    params = {'project': 'owner/repo', 'start': '2023-01-01', 'unique': True}
    query = GetUsage._construct_query(params)
    assert 'query' in query
    assert 'get_usage' in query
    assert 'project:"owner/repo"' in query
    assert 'start:"2023-01-01"' in query
    assert 'unique:true' in query


def test_concurrent_query_generation():
    """
    Simulate multiple threads generating queries concurrently.
    This would often fail if cls.query was shared across threads.
    """

    def gen_query(project_name):
        return CheckProject.generate_query(project=project_name, project_version='1.0.0')

    num_threads = 20
    num_queries = 100
    projects = [f'project-{i}' for i in range(num_queries)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(gen_query, projects))

    for i, res in enumerate(results):
        expected = f'project:"project-{i}"'
        assert expected in res, f'Query {i} corrupted: {res}'
