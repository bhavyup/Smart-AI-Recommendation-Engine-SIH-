from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(36), unique=True, index=True, nullable=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)  # optional
    education_level = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.JSON, nullable=False)  # List[str]
    sector_interests = db.Column(db.JSON, nullable=False)  # List[str]
    prefers_rural = db.Column(db.Boolean, default=False)
    from_rural_area = db.Column(db.Boolean, default=False)
    social_category = db.Column(db.String(20), default='')
    first_generation_graduate = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'uid': self.uid,  # include uid in API
            'name': self.name,
            'email': self.email,
            'education_level': self.education_level,
            'location': self.location,
            'skills': self.skills or [],
            'sector_interests': self.sector_interests or [],
            'prefers_rural': bool(self.prefers_rural),
            'from_rural_area': bool(self.from_rural_area),
            'social_category': self.social_category or '',
            'first_generation_graduate': bool(self.first_generation_graduate),
        }


class Internship(db.Model):
    __tablename__ = 'internships'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    sector = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    skills_required = db.Column(db.JSON, nullable=False)  # List[str]
    education_level = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    stipend = db.Column(db.Integer, nullable=False)
    rural_friendly = db.Column(db.Boolean, default=False)
    diversity_focused = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'sector': self.sector,
            'location': self.location,
            'skills_required': self.skills_required or [],
            'education_level': self.education_level,
            'capacity': self.capacity,
            'duration_months': self.duration_months,
            'stipend': self.stipend,
            'rural_friendly': bool(self.rural_friendly),
            'diversity_focused': bool(self.diversity_focused),
        }
