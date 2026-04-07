"""Curated taxonomy of skills, tools, and technologies for ATS matching."""
from typing import Dict, List, Set

# Technical programming languages
PROGRAMMING_LANGUAGES: List[str] = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Shell",
    "Bash", "PowerShell", "Groovy", "Lua", "Haskell", "Erlang", "Elixir", "Dart",
    "Objective-C", "Assembly", "COBOL", "Fortran", "SAS",
]

# Frontend frameworks and libraries
FRONTEND_FRAMEWORKS: List[str] = [
    "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt.js", "Gatsby",
    "React Native", "Flutter", "Ionic", "Ember", "Backbone", "jQuery",
    "HTML", "CSS", "SASS", "LESS", "Tailwind", "Bootstrap", "Material UI",
    "Styled Components", "Webpack", "Vite", "Rollup", "Babel", "Redux",
    "MobX", "Zustand", "GraphQL", "Apollo", "REST API", "WebSocket",
]

# Backend frameworks
BACKEND_FRAMEWORKS: List[str] = [
    "FastAPI", "Django", "Flask", "Express", "NestJS", "Spring Boot", "Spring",
    "Laravel", "Rails", "ASP.NET", ".NET Core", "Node.js", "Fastify",
    "Koa", "Hapi", "Gin", "Echo", "Fiber", "Actix", "Rocket", "Axum",
    "gRPC", "GraphQL", "REST", "Microservices", "Serverless",
]

# Databases
DATABASES: List[str] = [
    "PostgreSQL", "MySQL", "SQLite", "SQL Server", "Oracle", "MongoDB",
    "Redis", "Elasticsearch", "Cassandra", "DynamoDB", "Firebase",
    "Neo4j", "InfluxDB", "CockroachDB", "Supabase", "PlanetScale",
    "BigQuery", "Redshift", "Snowflake", "Databricks", "MariaDB",
    "SQL", "NoSQL", "ORM", "Prisma", "SQLAlchemy", "Hibernate",
]

# Cloud and DevOps
CLOUD_DEVOPS: List[str] = [
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Helm", "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI",
    "Travis CI", "ArgoCD", "Prometheus", "Grafana", "ELK Stack", "Datadog",
    "New Relic", "CloudFormation", "CDK", "Pulumi", "Vagrant", "Packer",
    "S3", "EC2", "Lambda", "ECS", "EKS", "RDS", "CloudFront", "Route 53",
    "IAM", "VPC", "Load Balancer", "Auto Scaling", "SQS", "SNS", "SES",
]

# AI and Machine Learning
AI_ML: List[str] = [
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "MLOps",
    "TensorFlow", "PyTorch", "Keras", "scikit-learn", "XGBoost", "LightGBM",
    "Hugging Face", "OpenAI", "LangChain", "LlamaIndex", "spaCy", "NLTK",
    "Pandas", "NumPy", "Matplotlib", "Seaborn", "Plotly", "Jupyter",
    "RAG", "LLM", "Fine-tuning", "Transformers", "BERT", "GPT", "Vector DB",
    "Pinecone", "Weaviate", "Chroma", "FAISS", "A/B Testing", "Feature Engineering",
]

# Version control and collaboration
VCS_COLLAB: List[str] = [
    "Git", "GitHub", "GitLab", "Bitbucket", "SVN", "Mercurial",
    "Jira", "Confluence", "Notion", "Slack", "Linear", "Asana", "Trello",
    "Code Review", "Pull Request", "Agile", "Scrum", "Kanban", "Sprint",
    "Stand-up", "Retrospective", "Story Points",
]

# Security
SECURITY: List[str] = [
    "OAuth", "JWT", "SSL/TLS", "HTTPS", "Encryption", "Authentication",
    "Authorization", "OWASP", "Penetration Testing", "Security Auditing",
    "SIEM", "SOC", "IAM", "Zero Trust", "Vulnerability Assessment",
    "GDPR", "SOC 2", "ISO 27001", "PCI DSS", "HIPAA",
]

# Soft skills
SOFT_SKILLS: List[str] = [
    "Leadership", "Communication", "Problem Solving", "Teamwork", "Collaboration",
    "Mentoring", "Project Management", "Stakeholder Management", "Cross-functional",
    "Time Management", "Prioritization", "Critical Thinking", "Adaptability",
    "Attention to Detail", "Analytical Thinking", "Strategic Thinking",
    "Presentation", "Technical Writing", "Documentation", "Code Review",
    "Pair Programming", "Coaching", "Negotiation", "Conflict Resolution",
]

# Certifications
CERTIFICATIONS: List[str] = [
    "AWS Certified", "Google Cloud Professional", "Azure Certified", "CKA", "CKAD",
    "Terraform Associate", "PMP", "Scrum Master", "CISSP", "CEH", "CompTIA",
    "Certified Data Scientist", "TensorFlow Developer", "Oracle Certified",
    "Salesforce Certified", "ITIL", "Six Sigma", "TOGAF",
]

# All skills flattened
ALL_SKILLS: Set[str] = set(
    PROGRAMMING_LANGUAGES
    + FRONTEND_FRAMEWORKS
    + BACKEND_FRAMEWORKS
    + DATABASES
    + CLOUD_DEVOPS
    + AI_ML
    + VCS_COLLAB
    + SECURITY
    + SOFT_SKILLS
    + CERTIFICATIONS
)

# Common aliases that should map to canonical skill names
SKILL_ALIASES: Dict[str, str] = {
    "react.js": "React", "reactjs": "React", "react js": "React",
    "vue.js": "Vue", "vuejs": "Vue", "vue js": "Vue",
    "angular.js": "Angular", "angularjs": "Angular",
    "next": "Next.js", "nextjs": "Next.js",
    "node": "Node.js", "nodejs": "Node.js", "node js": "Node.js",
    "express.js": "Express", "expressjs": "Express",
    "postgres": "PostgreSQL", "psql": "PostgreSQL",
    "mongo": "MongoDB", "mongo db": "MongoDB",
    "dynamodb": "DynamoDB", "dynamo db": "DynamoDB",
    "k8s": "Kubernetes", "kube": "Kubernetes",
    "tf": "Terraform",
    "gha": "GitHub Actions", "github action": "GitHub Actions",
    "ci/cd": "CI/CD", "cicd": "CI/CD", "ci cd": "CI/CD",
    "amazon web services": "AWS",
    "google cloud": "GCP", "google cloud platform": "GCP",
    "microsoft azure": "Azure",
    "ml": "Machine Learning", "deep learning": "Deep Learning",
    "nlp": "NLP", "natural language processing": "NLP",
    "cv": "Computer Vision",
    "sklearn": "scikit-learn", "sci-kit learn": "scikit-learn",
    "hf": "Hugging Face", "huggingface": "Hugging Face",
    "pytorch": "PyTorch", "torch": "PyTorch",
    "tensorflow": "TensorFlow", "tf2": "TensorFlow",
    "langchain": "LangChain",
    "tailwindcss": "Tailwind", "tailwind css": "Tailwind",
    "js": "JavaScript", "javascript": "JavaScript",
    "ts": "TypeScript", "typescript": "TypeScript",
    "cpp": "C++", "c plus plus": "C++",
    "csharp": "C#", "c sharp": "C#",
    "objective c": "Objective-C",
    "shell scripting": "Shell", "bash scripting": "Bash",
    "sql server": "SQL Server", "mssql": "SQL Server",
    "elasticsearch": "Elasticsearch", "elastic search": "Elasticsearch",
    "graphql": "GraphQL", "graph ql": "GraphQL",
    "rest api": "REST API", "restful": "REST API", "rest apis": "REST API",
    "websocket": "WebSocket", "websockets": "WebSocket",
    "grpc": "gRPC",
    "asp.net": "ASP.NET", "aspnet": "ASP.NET",
    ".net": ".NET Core", "dotnet": ".NET Core",
    "spring": "Spring", "springboot": "Spring Boot", "spring-boot": "Spring Boot",
    "fastapi": "FastAPI", "fast api": "FastAPI",
    "ruby on rails": "Rails",
    "amazon s3": "S3", "amazon ec2": "EC2", "amazon lambda": "Lambda",
    "oauth2": "OAuth", "oauth 2.0": "OAuth",
    "jwt": "JWT", "json web token": "JWT",
    "pair programming": "Pair Programming",
}

# Lowercase lookup for fast matching — includes both canonical skills and aliases
ALL_SKILLS_LOWER: Dict[str, str] = {skill.lower(): skill for skill in ALL_SKILLS}
for alias, canonical in SKILL_ALIASES.items():
    ALL_SKILLS_LOWER[alias.lower()] = canonical

SKILL_CATEGORIES: Dict[str, List[str]] = {
    "Technical": PROGRAMMING_LANGUAGES + BACKEND_FRAMEWORKS + FRONTEND_FRAMEWORKS + AI_ML,
    "Tool": DATABASES + CLOUD_DEVOPS + VCS_COLLAB + SECURITY,
    "Soft": SOFT_SKILLS,
    "Certification": CERTIFICATIONS,
}


def find_skill(text: str) -> str:
    """Return the canonical skill name if text matches any known skill (case-insensitive)."""
    return ALL_SKILLS_LOWER.get(text.lower().strip(), "")


def get_skill_category(skill: str) -> str:
    """Return the category for a given skill."""
    skill_lower = skill.lower()
    for category, skills in SKILL_CATEGORIES.items():
        if any(s.lower() == skill_lower for s in skills):
            return category
    return "Technical"
