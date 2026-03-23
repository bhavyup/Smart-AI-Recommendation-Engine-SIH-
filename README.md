# Smart AI Recommendation Engine

<p align="center"><strong>Enterprise-grade internship allocation intelligence for the PM Internship Scheme.</strong></p>
<p align="center">Designed for transparent matching, policy alignment, operational reliability, and measurable impact.</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-1B365D?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Application%20Layer-0B0F19?style=for-the-badge&logo=flask&logoColor=white">
  <img alt="Machine Learning" src="https://img.shields.io/badge/AI%20Engine-Scikit--learn-0E7490?style=for-the-badge">
  <img alt="Deployment" src="https://img.shields.io/badge/Deployment-Docker%20Ready-14532D?style=for-the-badge">
</p>

---

## Executive Summary

The Smart AI Recommendation Engine is a decision-support platform that matches candidates to internship opportunities using multi-factor scoring.

It is built to support large-scale public programs where allocation quality depends on both merit and policy priorities. The system combines technical fit signals with inclusion-aware criteria, then delivers recommendations through an easy-to-operate web platform for candidates and administrators.

### Strategic outcomes

- Improve candidate-opportunity fit quality
- Reduce manual effort in high-volume allocation workflows
- Enable transparent and explainable recommendation logic
- Align operations with affirmative-action and inclusion objectives
- Maintain operational continuity through resilient persistence modes

---

## Business Context

Internship allocation is not a single-variable ranking problem.
Effective matching requires balancing:

- Candidate skills and education compatibility
- Regional preference and location feasibility
- Sector alignment and interest relevance
- Capacity and placement constraints
- Diversity and inclusion policy commitments

This platform addresses these dimensions with a weighted, explainable scoring framework and production-ready service architecture.

---

## Capability Portfolio

| Capability Domain | Description |
|---|---|
| Intelligent Matching | AI-driven recommendation ranking with weighted components |
| Policy-Aware Allocation | Built-in support for diversity and rural-oriented considerations |
| Candidate Experience | Responsive input flow and real-time recommendation output |
| Administrative Operations | Dashboard-backed control surfaces and management APIs |
| Data Persistence | PostgreSQL primary with SQLite and file-based fallback pathways |
| Data Ingestion | CSV-driven internship import with replace and append strategies |
| Internationalization Readiness | Language support hooks and Unicode-safe processing |

---

## Solution Highlights

### 1. Allocation Intelligence

- Weighted multi-factor scoring model
- Skill relevance and profile compatibility checks
- Policy-sensitive recommendations with clear rationale
- Explainable output dimensions for stakeholder trust

### 2. Platform Operations

- Flask-based web and API service
- Robust fallback persistence behavior
- Snapshot and state continuity logic
- Production runtime support through Gunicorn

### 3. User Experience

- Streamlined candidate journey
- Clear recommendation reasons and match scores
- Mobile-compatible interfaces
- Admin workflows for data and internship lifecycle management

---

## Architecture Overview

### Application layers

- Presentation Layer: HTML templates and localized client scripts
- API Layer: Flask REST endpoints for candidate, internship, and recommendation operations
- Intelligence Layer: Smart allocation engine and scoring modules
- Persistence Layer: SQL database models plus file-state fallback

### Core components

| Component | Responsibility |
|---|---|
| app.py | Orchestration layer, routes, auth, persistence mode selection |
| smart_allocation_engine.py | Recommendation logic, scoring, ranking, model state |
| models.py | Candidate, Internship, and Shortlist data schema |
| language_support.py | Regional language support foundation |
| start.py | Startup assistance and dependency verification |
| gunicorn.conf.py | Runtime tuning for production serving |

---

## Repository Blueprint

| Path | Purpose |
|---|---|
| app.py | Main web application and API orchestration |
| models.py | SQLAlchemy schema definitions |
| smart_allocation_engine.py | AI matching engine |
| language_support.py | Localization support layer |
| start.py | Local launcher |
| requirements.txt | Dependency manifest |
| gunicorn.conf.py | Gunicorn worker/thread settings |
| templates/index.html | Candidate interface |
| templates/admin_dashboard.html | Admin interface |
| templates/login.html | Admin authentication view |
| templates/landing.html | Landing and navigation page |
| static/js/i18n.js | Client-side localization helpers |
| data/internships.csv | Seed internship dataset |
| data/engine.joblib | Serialized model and state snapshot |

---

## Matching Framework

The recommendation engine evaluates candidate-internship compatibility through weighted scoring dimensions.

### Weight distribution

- Skill Match: 30%
- Location Match: 20%
- Education Match: 20%
- Sector Match: 15%
- Diversity and Inclusion Factors: 15%

### Scoring expression

```text
Overall Score = (Skill * 0.30)
              + (Location * 0.20)
              + (Education * 0.20)
              + (Sector * 0.15)
              + (Diversity * 0.15)
```

### Dimension interpretation

- Skill: requirement overlap and relevance quality
- Location: preference alignment and regional suitability
- Education: qualification compatibility hierarchy
- Sector: candidate interest to internship domain match
- Diversity: inclusion-aware uplift according to supported criteria

---

## Data Model Specification

### Candidate

```python
{
    "name": str,
    "education_level": str,  # Diploma, Bachelor, Master, PhD
    "skills": list[str],
    "location": str,
    "sector_interests": list[str],
    "prefers_rural": bool,
    "from_rural_area": bool,
    "social_category": str,  # General, SC, ST, OBC
    "first_generation_graduate": bool
}
```

### Internship

```python
{
    "id": int,
    "title": str,
    "company": str,
    "sector": str,
    "location": str,
    "skills_required": list[str],
    "education_level": str,
    "capacity": int,
    "duration_months": int,
    "stipend": int,
    "rural_friendly": bool,
    "diversity_focused": bool
}
```

---

## API Surface

### Key endpoints

- GET /api/internships
- GET /api/candidates
- POST /api/recommendations
- GET /api/recommendations/by-email

### Recommendation request sample

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "education_level": "Bachelor",
  "skills": ["Python", "JavaScript"],
  "location": "Bangalore",
  "sector_interests": ["Technology"],
  "social_category": "General",
  "prefers_rural": false,
  "from_rural_area": false,
  "first_generation_graduate": false
}
```

### Recommendation response sample

```json
{
  "success": true,
  "candidate_id": 1,
  "recommendations": [
    {
      "internship": {},
      "scores": {
        "overall": 0.85,
        "skill_match": 0.75,
        "location_match": 1.0,
        "education_match": 1.0,
        "sector_match": 1.0,
        "diversity_bonus": 0.0
      },
      "match_reasons": [
        "Strong skill alignment",
        "Perfect location match"
      ]
    }
  ]
}
```

---

## Runtime and Persistence Strategy

The platform supports layered persistence for reliability across environments:

1. PostgreSQL as preferred production-grade persistence
2. SQLite fallback for constrained or local environments
3. File-based fallback using JSON and joblib snapshots when DB services are unavailable

This approach enables graceful degradation while preserving service continuity.

---

## Candidate and Admin Workflows

### Candidate workflow

1. Submit profile, skills, education, and preferences
2. Receive ranked recommendations in real time
3. Review reason codes and shortlist opportunities

### Admin workflow

1. Authenticate through admin login
2. Access system management dashboard
3. Oversee internships, candidates, and operational metrics

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Setup

```bash
git clone <repository-url>
cd Smart-AI-Recommendation-Engine-SIH-
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

### Access

- Landing: http://localhost:5000/
- Candidate Portal: http://localhost:5000/candidate
- Admin Login: http://localhost:5000/login

---

## Testing and Validation

### Application run test

```bash
python app.py
```

### Engine load verification

```bash
python -c "from smart_allocation_engine import SmartAllocationEngine; e=SmartAllocationEngine(); print('Engine loaded successfully')"
```

### API smoke test

```bash
curl http://localhost:5000/api/internships
```

---

## Deployment Readiness

### Production-style local run

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Containerized run

```bash
docker build -t smart-allocation-engine .
docker run -p 5000:5000 smart-allocation-engine
```

---

## Localization Readiness

The system includes foundational support for multilingual expansion:

- Modular language support integration
- UTF-8 safe content pipeline
- Client-side translation utility hooks

---

## Sample Data Coverage

Current project data illustrates:

- Multi-sector internship distribution
- Diverse candidate profiles and constraints
- Regionally varied placement opportunities
- Inclusion-oriented metadata for policy alignment

---

## Roadmap

### Product roadmap

- Advanced ranking model enhancements
- Analytics and policy-performance dashboards
- Richer interaction channels for stakeholders
- Native mobile experience

### Platform roadmap

- Redis-backed caching layer
- Horizontal scaling and load balancing
- Enhanced observability and diagnostics
- Service decomposition for enterprise scale

---

## Contribution Guidelines

1. Fork repository
2. Create feature branch
3. Implement and test changes
4. Submit pull request with clear rationale

### Quality standards

- Follow PEP 8 conventions
- Use explicit, meaningful naming
- Add docstrings where needed
- Prefer type hints for maintainability

---

## License

Developed under Smart India Hackathon context for PM Internship Scheme alignment.

---

## Team and Domain Context

- Theme: AI-Based Smart Allocation Engine for PM Internship Scheme
- Sector: Ministry of Corporate Affairs context
- Contributors: project team and collaborating developers

---

## Support

- Open an issue for defects or feature requests
- Provide reproducible steps and expected outcomes
- Attach logs/screenshots for faster triage

---

<p align="center"><strong>Built to operationalize fairness, quality, and scale in internship allocation.</strong></p>
