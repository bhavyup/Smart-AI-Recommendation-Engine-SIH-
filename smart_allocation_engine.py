import os
import ast
import json
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
from typing import List, Dict, Any


class SmartAllocationEngine:
    """
    AI-based Smart Allocation Engine for PM Internship Scheme
    Matches candidates with internship opportunities using TF-IDF (skills) + heuristics.
    """

    def __init__(self):
        self.candidate_data: List[Dict[str, Any]] = []
        self.internship_data: List[Dict[str, Any]] = []
        # TF-IDF internals
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.skill_matrix = None  # rows aligned with internship_data order
        # Weights; use 100-scale internally
        self.weights = {'skill': 30, 'location': 20,
                        'education': 20, 'sector': 15, 'diversity': 15}
        self.model_trained = False

    # ---------------- CSV + Sample loaders ----------------
    def load_internship_data_from_csv(self, filepath: str) -> bool:
        """
        Load internships from CSV and train TF-IDF on skills_required.
        Expected columns: id,title,company,sector,location,skills_required (list-like string),education_level,capacity,duration_months,stipend,rural_friendly,diversity_focused
        """
        if not filepath or not os.path.exists(filepath):
            return False
        df = pd.read_csv(filepath)
        self.internship_data = []
        skill_texts = []

        for _, row in df.iterrows():
            try:
                skills = row['skills_required']
                if isinstance(skills, str):
                    # allow json-like or python-list-like
                    try:
                        skills_list = json.loads(skills)
                        if not isinstance(skills_list, list):
                            skills_list = []
                    except Exception:
                        skills_list = ast.literal_eval(
                            skills) if skills.strip() else []
                elif isinstance(skills, list):
                    skills_list = skills
                else:
                    skills_list = []

                internship = {
                    'id': int(row.get('id')) if not pd.isna(row.get('id')) else None,
                    'title': str(row.get('title', '')).strip(),
                    'company': str(row.get('company', '')).strip(),
                    'sector': str(row.get('sector', '')).strip(),
                    'location': str(row.get('location', '')).strip(),
                    'skills_required': [str(s).strip() for s in skills_list if str(s).strip()],
                    'education_level': str(row.get('education_level', 'Bachelor')).strip(),
                    'capacity': int(row.get('capacity') or 0),
                    'duration_months': int(row.get('duration_months') or 0),
                    'stipend': int(row.get('stipend') or 0),
                    'rural_friendly': bool(row.get('rural_friendly')),
                    'diversity_focused': bool(row.get('diversity_focused')),
                }
                self.internship_data.append(internship)
                skill_texts.append(
                    ' '.join(internship['skills_required']).lower())
            except Exception:
                # skip bad rows
                continue

        # Assign IDs if missing or non-unique
        seen = set()
        for i, it in enumerate(self.internship_data, start=1):
            if not it.get('id') or it['id'] in seen:
                it['id'] = i
            seen.add(it['id'])

        # Train TF-IDF
        if skill_texts:
            self.skill_matrix = self.vectorizer.fit_transform(skill_texts)
        else:
            self.skill_matrix = None

        self.model_trained = True
        return True

    def load_sample_data(self):
        """Load built-in sample internship data (fallback)."""
        self.internship_data = [
            {'id': 1, 'title': 'Software Development Intern', 'company': 'TechCorp India', 'sector': 'Technology',
             'location': 'Bangalore', 'skills_required': ['Python', 'JavaScript', 'React', 'SQL'], 'education_level': 'Bachelor',
             'capacity': 5, 'duration_months': 6, 'stipend': 15000, 'rural_friendly': True, 'diversity_focused': True},
            {'id': 2, 'title': 'Data Science Intern', 'company': 'DataAnalytics Ltd', 'sector': 'Technology',
             'location': 'Mumbai', 'skills_required': ['Python', 'Machine Learning', 'Statistics', 'Pandas'], 'education_level': 'Master',
             'capacity': 3, 'duration_months': 4, 'stipend': 20000, 'rural_friendly': False, 'diversity_focused': True},
            {'id': 3, 'title': 'Marketing Intern', 'company': 'BrandBuilders', 'sector': 'Marketing',
             'location': 'Delhi', 'skills_required': ['Digital Marketing', 'Social Media', 'Content Writing', 'Analytics'],
             'education_level': 'Bachelor', 'capacity': 4, 'duration_months': 3, 'stipend': 12000, 'rural_friendly': True, 'diversity_focused': False},
            {'id': 4, 'title': 'Finance Intern', 'company': 'FinTech Solutions', 'sector': 'Finance',
             'location': 'Chennai', 'skills_required': ['Excel', 'Financial Analysis', 'Accounting', 'PowerBI'], 'education_level': 'Bachelor',
             'capacity': 2, 'duration_months': 5, 'stipend': 18000, 'rural_friendly': False, 'diversity_focused': True},
            {'id': 5, 'title': 'Healthcare Research Intern', 'company': 'MedResearch Institute', 'sector': 'Healthcare',
             'location': 'Hyderabad', 'skills_required': ['Research', 'Data Analysis', 'Medical Knowledge', 'Python'], 'education_level': 'Master',
             'capacity': 3, 'duration_months': 6, 'stipend': 16000, 'rural_friendly': True, 'diversity_focused': True},
        ]
        # Train TF-IDF on sample
        texts = [' '.join(it['skills_required']).lower()
                 for it in self.internship_data]
        self.skill_matrix = self.vectorizer.fit_transform(
            texts) if texts else None
        self.model_trained = True

    # ---------------- Candidates ----------------
    def add_candidate(self, candidate_info: Dict[str, Any]):
        candidate_id = len(self.candidate_data) + 1
        candidate_info = dict(candidate_info)
        candidate_info['id'] = candidate_id
        self.candidate_data.append(candidate_info)
        return candidate_id

    # ---------------- Scoring ----------------
    def set_weights(self, weights: Dict[str, int]):
        """
        Accepts any scale, normalizes to 100 internally: keys skill,location,education,sector,diversity
        """
        w = {k: max(0, int(weights.get(k, 0))) for k in [
            'skill', 'location', 'education', 'sector', 'diversity']}
        total = sum(w.values()) or 1
        self.weights = {k: int(round(v / total * 100)) for k, v in w.items()}

    def calculate_skill_match_score(self, candidate_skills: List[str], internship: Dict[str, Any]) -> float:
        # If TF-IDF available, use cosine similarity
        if self.skill_matrix is not None and hasattr(self.vectorizer, 'transform'):
            try:
                candidate_text = ' '.join(candidate_skills or []).lower()
                idx = self._internship_index(internship)
                if idx is None:
                    return 0.0
                candidate_vec = self.vectorizer.transform([candidate_text])
                return float(cosine_similarity(candidate_vec, self.skill_matrix[idx]).ravel()[0])
            except Exception:
                pass
        # Fallback: simple overlap
        if not candidate_skills or not internship.get('skills_required'):
            return 0.0
        cand = [s.lower() for s in candidate_skills]
        ints = [s.lower() for s in internship.get('skills_required', [])]
        matches = sum(1 for s in ints if s in cand)
        return matches / max(1, len(ints))

    def _internship_index(self, internship: Dict[str, Any]):
        # index aligns with self.internship_data
        try:
            iid = internship.get('id')
            for idx, it in enumerate(self.internship_data):
                if it.get('id') == iid:
                    return slice(idx, idx+1)
        except Exception:
            return None
        return None

    def calculate_location_preference_score(self, candidate_location: str, internship_location: str,
                                            candidate_prefers_rural: bool, internship_rural_friendly: bool) -> float:
        if (candidate_location or '').strip().lower() == (internship_location or '').strip().lower():
            return 1.0
        if candidate_prefers_rural and internship_rural_friendly:
            return 0.8
        return 0.6

    def calculate_diversity_score(self, candidate_info: Dict[str, Any], internship_info: Dict[str, Any]) -> float:
        score = 0.0
        if internship_info.get('diversity_focused', False):
            score += 0.3
        if candidate_info.get('from_rural_area', False):
            score += 0.2
        if (candidate_info.get('social_category') or '') in ['SC', 'ST', 'OBC']:
            score += 0.2
        if candidate_info.get('first_generation_graduate', False):
            score += 0.1
        return min(score, 1.0)

    def calculate_education_match_score(self, candidate_education: str, internship_education: str) -> float:
        levels = {'Diploma': 1, 'Bachelor': 2, 'Master': 3, 'PhD': 4}
        c = levels.get(candidate_education, 2)
        i = levels.get(internship_education, 2)
        if c == i:
            return 1.0
        if c > i:
            return 0.8
        return 0.4

    def calculate_sector_interest_score(self, candidate_interests: List[str], internship_sector: str) -> float:
        if not candidate_interests:
            return 0.5
        return 1.0 if (internship_sector or '').lower() in [s.lower() for s in candidate_interests] else 0.3

    def get_recommendations(self, candidate_info: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
        if not self.internship_data:
            self.load_sample_data()

        # weight fractions
        wf = {k: v / 100.0 for k, v in self.weights.items()}
        recs = []
        for it in self.internship_data:
            s = self.calculate_skill_match_score(
                candidate_info.get('skills', []), it)
            l = self.calculate_location_preference_score(candidate_info.get('location', ''), it.get('location', ''),
                                                         bool(candidate_info.get(
                                                             'prefers_rural', False)),
                                                         bool(it.get('rural_friendly', False)))
            e = self.calculate_education_match_score(candidate_info.get(
                'education_level', 'Bachelor'), it.get('education_level', 'Bachelor'))
            sec = self.calculate_sector_interest_score(
                candidate_info.get('sector_interests', []), it.get('sector', ''))
            d = self.calculate_diversity_score(candidate_info, it)

            overall = s * wf['skill'] + l * wf['location'] + e * \
                wf['education'] + sec * wf['sector'] + d * wf['diversity']
            recs.append({
                'internship': it,
                'scores': {
                    'overall': round(overall, 3),
                    'skill_match': round(s, 3),
                    'location_match': round(l, 3),
                    'education_match': round(e, 3),
                    'sector_match': round(sec, 3),
                    'diversity_bonus': round(d, 3),
                },
                'match_reasons': self._generate_match_reasons(s, l, e, sec, d)
            })

        recs.sort(key=lambda x: x['scores']['overall'], reverse=True)
        return self.make_json_serializable(recs[:top_n])

    def _generate_match_reasons(self, s, l, e, sec, d):
        reasons = []
        if s > 0.7:
            reasons.append("Strong skill alignment")
        elif s > 0.4:
            reasons.append("Good skill match")
        if l > 0.8:
            reasons.append("Perfect location match")
        elif l > 0.6:
            reasons.append("Good location fit")
        if e > 0.8:
            reasons.append("Education level matches")
        if sec > 0.8:
            reasons.append("Matches your sector interests")
        if d > 0.3:
            reasons.append("Supports diversity and inclusion")
        return reasons

    # ---------------- Persistence ----------------
    def save_model(self, filepath: str):
        joblib.dump({
            'candidate_data': self.candidate_data,
            'internship_data': self.internship_data,
            'model_trained': self.model_trained,
            'weights': self.weights
        }, filepath)

    def load_model(self, filepath: str):
        model_data = joblib.load(filepath)
        self.candidate_data = model_data.get('candidate_data', [])
        self.internship_data = model_data.get('internship_data', [])
        self.model_trained = model_data.get('model_trained', False)
        self.weights = model_data.get('weights', self.weights)
        # Rebuild TF-IDF if internships exist
        texts = [' '.join(it.get('skills_required', []))
                 for it in self.internship_data]
        self.skill_matrix = self.vectorizer.fit_transform(
            [t.lower() for t in texts]) if texts else None

    def rebuild_tfidf(self):
        texts = [' '.join(it.get('skills_required', []))
                for it in (self.internship_data or [])]
        self.skill_matrix = self.vectorizer.fit_transform(
            [t.lower() for t in texts]) if texts else None

    # JSON-safe
    def make_json_serializable(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, dict):
            return {k: self.make_json_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.make_json_serializable(i) for i in obj]
        return obj
