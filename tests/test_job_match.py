import pytest
from uuid import uuid4
from unittest.mock import MagicMock
from app.job_matching.service import JobMatchingService

@pytest.fixture
def service():
    return JobMatchingService(db=None)

def test_normalization(service):
    items = ["React ", "reactjs", "  node.js", "React"]
    normalized = service.normalize_list(items)
    # Note: my service doesn't have a sophisticated synonym mapper like reactjs -> react yet
    # but it should handle casing and trimming
    assert "react" in normalized
    assert "reactjs" in normalized
    assert "node.js" in normalized
    assert len(normalized) == 3

def test_skill_score(service):
    user_skills = ["react", "node", "python"]
    job_required = ["react", "node", "typescript"]
    
    score = service.calculate_skill_score(user_skills, job_required)
    # 2 matched / 3 required = 0.666...
    assert score == pytest.approx(0.666, 0.01)

def test_interest_score_tags(service):
    user_interests = ["backend", "cloud"]
    job_tags = ["backend", "fintech"]
    job_title = "Software Engineer"
    
    score = service.calculate_interest_score(user_interests, job_tags, job_title)
    assert score == 0.3

def test_interest_score_title(service):
    user_interests = ["frontend"]
    job_tags = ["web"]
    job_title = "Frontend Developer"
    
    score = service.calculate_interest_score(user_interests, job_tags, job_title)
    assert score == 0.3

def test_experience_score(service):
    # Case: Junior user, junior job
    score = service.calculate_experience_score(True, "0-1 years of experience")
    assert score == 0.1
    
    # Case: Senior job
    score = service.calculate_experience_score(True, "5+ years of experience")
    assert score == 0.0

def test_total_score_calculation(service):
    # Hand-calculated example:
    # User: skills=[react, node], interests=[backend]
    # Job: required=[react, node, postgres], tags=[backend], exp="Fresher"
    
    user_skills = ["react", "node"]
    job_required = ["react", "node", "postgres"]
    user_interests = ["backend"]
    job_tags = ["backend"]
    job_title = "Junior Backend Developer"
    
    skill_score = service.calculate_skill_score(user_skills, job_required) # 2/3 = 0.666
    interest_score = service.calculate_interest_score(user_interests, job_tags, job_title) # 0.3
    exp_score = service.calculate_experience_score(True, "Fresher") # 0.1
    
    total = (skill_score * 0.6) + (interest_score * 0.3) + (exp_score * 0.1)
    # (0.666 * 0.6) + (0.3 * 0.3) + (0.1 * 0.1)
    # 0.4 + 0.09 + 0.01 = 0.5
    
    assert total == pytest.approx(0.5, 0.01)
    assert service.get_match_label(total) == "Upskill and apply"
