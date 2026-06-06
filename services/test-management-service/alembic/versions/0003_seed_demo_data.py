"""seed demo data

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05

Data migration: demo skills, tests, test submissions, and categories
(with category->skill links) for local development. Replaces the old
seed_db.py startup script.

- Idempotent per table: a table that already has rows is skipped, so
  pre-existing dev volumes (seeded by the old script) are untouched.
- Demo users live in the shared database but belong to user-service,
  which seeds them on its startup. In docker compose this service waits
  on user-service's healthcheck, so the trainer/participant lookups
  below are satisfied. If no trainer exists the migration raises —
  Alembic then does NOT record 0003 as applied, the container exits,
  and compose restarts it (self-healing retry).
"""
from datetime import datetime, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (name, description) — ported verbatim from the old seed_db.py
SKILLS_DATA = [
        # Programming Languages
        ('Java', 'Object-oriented programming language'),
        ('Python', 'High-level programming language'),
        ('JavaScript', 'Client and server-side scripting language'),
        ('TypeScript', 'Typed superset of JavaScript'),
        ('C#', 'Multi-paradigm programming language'),
        ('C++', 'General-purpose programming language'),
        ('C', 'Procedural programming language'),
        ('Go', 'Statically typed compiled language'),
        ('Rust', 'Memory-safe systems programming language'),
        ('Ruby', 'Dynamic object-oriented language'),
        ('PHP', 'Server-side scripting language'),
        ('Swift', 'Apple platform programming language'),
        ('Kotlin', 'Modern language for Android development'),
        ('Scala', 'JVM-based functional programming language'),
        ('R', 'Statistical computing language'),
        ('MATLAB', 'Numerical computing environment'),

        # Frontend Frameworks & Libraries
        ('React', 'JavaScript library for building UIs'),
        ('Angular', 'TypeScript-based web framework'),
        ('Vue.js', 'Progressive JavaScript framework'),
        ('Svelte', 'Component-based JavaScript framework'),
        ('Next.js', 'React framework for production'),
        ('Nuxt.js', 'Vue.js framework'),
        ('jQuery', 'JavaScript library for DOM manipulation'),
        ('Redux', 'State management library'),
        ('MobX', 'Simple state management'),
        ('RxJS', 'Reactive programming library'),

        # Backend Frameworks
        ('Spring Boot', 'Java application framework'),
        ('Django', 'Python web framework'),
        ('Flask', 'Python micro web framework'),
        ('FastAPI', 'Modern Python web framework'),
        ('Express.js', 'Node.js web framework'),
        ('NestJS', 'Progressive Node.js framework'),
        ('Ruby on Rails', 'Ruby web framework'),
        ('ASP.NET Core', '.NET web framework'),
        ('Laravel', 'PHP web framework'),
        ('Gin', 'Go web framework'),

        # Databases
        ('PostgreSQL', 'Advanced open-source relational database'),
        ('MySQL', 'Open-source relational database'),
        ('MongoDB', 'NoSQL document database'),
        ('Redis', 'In-memory data structure store'),
        ('Cassandra', 'Distributed NoSQL database'),
        ('DynamoDB', 'AWS NoSQL database'),
        ('SQLite', 'Embedded relational database'),
        ('Oracle Database', 'Enterprise relational database'),
        ('Microsoft SQL Server', 'Relational database management system'),
        ('MariaDB', 'MySQL fork relational database'),
        ('Elasticsearch', 'Search and analytics engine'),
        ('CouchDB', 'NoSQL document database'),
        ('Neo4j', 'Graph database'),
        ('TimescaleDB', 'Time-series database'),

        # Cloud Platforms & Services
        ('AWS', 'Amazon Web Services cloud platform'),
        ('Azure', 'Microsoft cloud computing platform'),
        ('Google Cloud Platform', 'GCP cloud services'),
        ('AWS Lambda', 'Serverless compute service'),
        ('AWS S3', 'Object storage service'),
        ('AWS EC2', 'Virtual server hosting'),
        ('AWS RDS', 'Managed relational database'),
        ('AWS ECS', 'Container orchestration service'),
        ('AWS CloudFormation', 'Infrastructure as code'),
        ('Azure Functions', 'Serverless compute'),
        ('Azure DevOps', 'Development collaboration tools'),
        ('Google App Engine', 'Platform as a service'),
        ('Google Cloud Functions', 'Serverless execution environment'),
        ('Firebase', 'Backend-as-a-service platform'),
        ('Heroku', 'Platform as a service'),
        ('DigitalOcean', 'Cloud infrastructure provider'),

        # DevOps & CI/CD
        ('Docker', 'Container platform'),
        ('Kubernetes', 'Container orchestration'),
        ('Jenkins', 'Automation server'),
        ('GitLab CI/CD', 'Continuous integration/deployment'),
        ('GitHub Actions', 'CI/CD automation'),
        ('CircleCI', 'Continuous integration platform'),
        ('Travis CI', 'CI/CD service'),
        ('Terraform', 'Infrastructure as code tool'),
        ('Ansible', 'Configuration management tool'),
        ('Puppet', 'Configuration management'),
        ('Chef', 'Infrastructure automation'),
        ('Vagrant', 'Development environment manager'),
        ('Helm', 'Kubernetes package manager'),
        ('Prometheus', 'Monitoring and alerting'),
        ('Grafana', 'Analytics and visualization'),
        ('Nagios', 'IT infrastructure monitoring'),

        # Version Control & Collaboration
        ('Git', 'Distributed version control system'),
        ('GitHub', 'Git repository hosting'),
        ('GitLab', 'DevOps platform'),
        ('Bitbucket', 'Git solution for teams'),
        ('Subversion', 'Version control system'),
        ('Jira', 'Project management tool'),
        ('Confluence', 'Team collaboration software'),
        ('Slack', 'Team communication platform'),

        # Testing
        ('JUnit', 'Java testing framework'),
        ('TestNG', 'Testing framework'),
        ('Mockito', 'Java mocking framework'),
        ('Jest', 'JavaScript testing framework'),
        ('Mocha', 'JavaScript test framework'),
        ('Chai', 'Assertion library'),
        ('Selenium', 'Browser automation'),
        ('Cypress', 'End-to-end testing'),
        ('Playwright', 'Browser automation framework'),
        ('JMeter', 'Load testing tool'),
        ('Postman', 'API testing tool'),
        ('PyTest', 'Python testing framework'),
        ('RSpec', 'Ruby testing tool'),
        ('Karma', 'Test runner for JavaScript'),

        # Data Science & ML
        ('TensorFlow', 'Machine learning framework'),
        ('PyTorch', 'Deep learning framework'),
        ('Scikit-learn', 'Machine learning library'),
        ('Pandas', 'Data analysis library'),
        ('NumPy', 'Numerical computing library'),
        ('Keras', 'Deep learning API'),
        ('Apache Spark', 'Unified analytics engine'),
        ('Hadoop', 'Distributed storage and processing'),
        ('Jupyter', 'Interactive computing environment'),
        ('Matplotlib', 'Plotting library'),
        ('Seaborn', 'Statistical data visualization'),
        ('NLTK', 'Natural language processing'),
        ('OpenCV', 'Computer vision library'),
        ('spaCy', 'Industrial NLP library'),

        # Web Technologies
        ('HTML', 'Hypertext markup language'),
        ('CSS', 'Cascading style sheets'),
        ('SASS', 'CSS preprocessor'),
        ('Less', 'CSS preprocessor'),
        ('Tailwind CSS', 'Utility-first CSS framework'),
        ('Bootstrap', 'CSS framework'),
        ('Material-UI', 'React UI framework'),
        ('Ant Design', 'React UI library'),
        ('WebSockets', 'Real-time communication protocol'),
        ('GraphQL', 'Query language for APIs'),
        ('REST API', 'Representational State Transfer'),
        ('gRPC', 'Remote procedure call framework'),
        ('OAuth', 'Authorization framework'),
        ('JWT', 'JSON Web Tokens'),

        # Message Brokers & Queues
        ('RabbitMQ', 'Message broker'),
        ('Apache Kafka', 'Distributed event streaming'),
        ('AWS SQS', 'Message queuing service'),
        ('AWS SNS', 'Notification service'),
        ('Apache ActiveMQ', 'Message broker'),
        ('NATS', 'Cloud native messaging system'),

        # API & Integration
        ('Swagger', 'API documentation tool'),
        ('Postman', 'API development environment'),
        ('Apigee', 'API management platform'),
        ('Kong', 'API gateway'),
        ('MuleSoft', 'Integration platform'),
        ('Apache Camel', 'Integration framework'),

        # Security
        ('Cryptography', 'Secure communication techniques'),
        ('SSL/TLS', 'Security protocols'),
        ('Penetration Testing', 'Security testing'),
        ('OWASP', 'Web application security'),
        ('Kerberos', 'Network authentication protocol'),
        ('IAM', 'Identity and access management'),
        ('SSO', 'Single sign-on'),
        ('SAML', 'Security assertion markup language'),

        # Architectural Patterns
        ('Microservices', 'Architectural style'),
        ('Event-Driven Architecture', 'Design pattern'),
        ('Domain-Driven Design', 'Software design approach'),
        ('CQRS', 'Command query responsibility segregation'),
        ('Service-Oriented Architecture', 'SOA design pattern'),
        ('Serverless Architecture', 'Cloud computing model'),
        ('Monolithic Architecture', 'Single-tier software application'),

        # Software Engineering Practices
        ('Agile', 'Software development methodology'),
        ('Scrum', 'Agile framework'),
        ('Kanban', 'Workflow management method'),
        ('TDD', 'Test-driven development'),
        ('BDD', 'Behavior-driven development'),
        ('CI/CD', 'Continuous integration/deployment'),
        ('Code Review', 'Software quality practice'),
        ('Pair Programming', 'Development technique'),
        ('Design Patterns', 'Software design solutions'),
        ('SOLID Principles', 'Object-oriented design'),
        ('Clean Code', 'Software craftsmanship'),
        ('Refactoring', 'Code improvement technique'),

        # Mobile Development
        ('Android Development', 'Mobile app development'),
        ('iOS Development', 'Apple mobile development'),
        ('React Native', 'Cross-platform mobile framework'),
        ('Flutter', 'UI toolkit for mobile'),
        ('Xamarin', 'Cross-platform development'),
        ('Ionic', 'Hybrid mobile app framework'),
        ('SwiftUI', 'UI toolkit for Apple platforms'),

        # Big Data & Analytics
        ('Apache Flink', 'Stream processing framework'),
        ('Apache Storm', 'Real-time computation system'),
        ('Tableau', 'Data visualization tool'),
        ('Power BI', 'Business analytics service'),
        ('Apache Hive', 'Data warehouse software'),
        ('Presto', 'Distributed SQL query engine'),
        ('Snowflake', 'Cloud data warehouse'),
]

# (name, test_type, role, curriculum, duration, number_of_questions, active)
TESTS_DATA = [
    ('Java Fundamentals Quiz', 'QUIZ', 'Java Developer', 'Full Stack Java', timedelta(minutes=45), 20, True),
    ('Python Data Structures Quiz', 'QUIZ', 'Python Developer', 'Python Full Stack', timedelta(hours=1), 25, True),
    ('System Design Interview', 'INTERVIEW', 'Senior Developer', 'System Design', timedelta(minutes=30), None, True),
    ('React Components Assessment', 'QUIZ', 'Frontend Developer', 'React Frontend', timedelta(minutes=40), 15, True),
    ('Behavioral Interview', 'INTERVIEW', 'Software Engineer', 'Soft Skills', timedelta(minutes=25), None, True),
    ('Advanced Java Quiz', 'QUIZ', 'Senior Java Developer', 'Full Stack Java', timedelta(minutes=50), 30, True),
]

# name -> (description, [linked skill names])
CATEGORIES_DATA = {
    'Python': (
        'Python language and ecosystem',
        ['Python', 'Django', 'Flask', 'FastAPI', 'PyTest', 'Pandas', 'NumPy'],
    ),
    'Docker': (
        'Containers and orchestration',
        ['Docker', 'Kubernetes', 'Helm', 'Terraform'],
    ),
    'Algorithms': (
        'Data structures, algorithms, and problem solving',
        ['Design Patterns', 'SOLID Principles', 'TDD'],
    ),
}


def _count(conn, table: str) -> int:
    return conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()


def _seed_skills(conn) -> None:
    if _count(conn, "skills") > 0:
        print("skills already populated, skipping seed")
        return
    conn.execute(
        sa.text("INSERT INTO skills (name, description) VALUES (:name, :description)"),
        [{"name": n, "description": d} for n, d in SKILLS_DATA],
    )
    print(f"seeded {len(SKILLS_DATA)} skills")


def _trainer_id(conn) -> int:
    """First TRAINER user. users is owned/seeded by user-service — see module
    docstring for the ordering contract."""
    has_users_table = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'users' AND table_schema = current_schema()"
        )
    ).scalar()
    trainer = (
        conn.execute(
            sa.text("SELECT id FROM users WHERE role = 'TRAINER' ORDER BY id LIMIT 1")
        ).scalar()
        if has_users_table
        else None
    )
    if trainer is None:
        raise RuntimeError(
            "Cannot seed demo tests/submissions: no TRAINER user found. "
            "user-service seeds demo users on its startup — start it first "
            "(docker compose orders this automatically via its healthcheck)."
        )
    return trainer


def _seed_tests(conn) -> None:
    if _count(conn, "tests") > 0:
        print("tests already populated, skipping seed")
        return
    trainer_id = _trainer_id(conn)
    now = datetime.utcnow()
    conn.execute(
        sa.text(
            "INSERT INTO tests (name, test_type, role, curriculum, duration, "
            "number_of_questions, created_by_id, active, created_at, updated_at) "
            "VALUES (:name, :test_type, :role, :curriculum, :duration, "
            ":number_of_questions, :created_by_id, :active, :created_at, :updated_at)"
        ),
        [
            {
                "name": name,
                "test_type": test_type,
                "role": role,
                "curriculum": curriculum,
                "duration": duration,
                "number_of_questions": number_of_questions,
                "created_by_id": trainer_id,
                "active": active,
                "created_at": now,
                "updated_at": now,
            }
            for name, test_type, role, curriculum, duration, number_of_questions, active in TESTS_DATA
        ],
    )
    print(f"seeded {len(TESTS_DATA)} tests")


def _seed_test_submissions(conn) -> None:
    if _count(conn, "test_submissions") > 0:
        print("test_submissions already populated, skipping seed")
        return
    trainer_id = _trainer_id(conn)
    test_ids = [r[0] for r in conn.execute(sa.text("SELECT id FROM tests ORDER BY id"))]
    participant_ids = [
        r[0]
        for r in conn.execute(
            sa.text("SELECT id FROM users WHERE role = 'PARTICIPANT' ORDER BY id")
        )
    ]
    if not test_ids or not participant_ids:
        print("no tests or participants found, skipping submission seed")
        return

    now = datetime.utcnow()
    rows = []
    for test_id in test_ids:
        for i, participant_id in enumerate(participant_ids):
            if i == 0:  # first participant — completed
                status, ai, final = "COMPLETED", 85, 85
                started = now - timedelta(days=2)
                submitted = started + timedelta(minutes=30)
            elif i == 1:  # second — in progress
                status, ai, final = "IN_PROGRESS", None, None
                started, submitted = now - timedelta(hours=1), None
            elif i == 2:  # third — completed
                status, ai, final = "COMPLETED", 92, 92
                started = now - timedelta(days=1)
                submitted = started + timedelta(minutes=25)
            else:  # rest — assigned
                status, ai, final = "ASSIGNED", None, None
                started, submitted = None, None
            rows.append(
                {
                    "test_id": test_id,
                    "user_id": participant_id,
                    "assigned_by_id": trainer_id,
                    "assigned_at": now - timedelta(days=3),
                    "due_date": now + timedelta(days=7),
                    "status": status,
                    "started_at": started,
                    "submitted_at": submitted,
                    "ai_score": ai,
                    "final_score": final,
                    "feedback": "Good performance" if status == "COMPLETED" else None,
                    "created_at": now,
                    "updated_at": now,
                }
            )
    conn.execute(
        sa.text(
            "INSERT INTO test_submissions (test_id, user_id, assigned_by_id, "
            "assigned_at, due_date, status, started_at, submitted_at, ai_score, "
            "final_score, feedback, created_at, updated_at) "
            "VALUES (:test_id, :user_id, :assigned_by_id, :assigned_at, :due_date, "
            ":status, :started_at, :submitted_at, :ai_score, :final_score, "
            ":feedback, :created_at, :updated_at)"
        ),
        rows,
    )
    print(f"seeded {len(rows)} test submissions")


def _seed_categories(conn) -> None:
    if _count(conn, "categories") > 0:
        print("categories already populated, skipping seed")
        return
    for name, (description, skill_names) in CATEGORIES_DATA.items():
        category_id = conn.execute(
            sa.text(
                "INSERT INTO categories (name, description) "
                "VALUES (:name, :description) RETURNING id"
            ),
            {"name": name, "description": description},
        ).scalar()
        skill_ids = [
            r[0]
            for r in conn.execute(
                sa.text("SELECT id FROM skills WHERE name = ANY(:names)"),
                {"names": skill_names},
            )
        ]
        if skill_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO category_skills (category_id, skill_id) "
                    "VALUES (:category_id, :skill_id)"
                ),
                [{"category_id": category_id, "skill_id": s} for s in skill_ids],
            )
    print(f"seeded {len(CATEGORIES_DATA)} categories with skill links")


def upgrade() -> None:
    """Seed demo data (idempotent per table)."""
    conn = op.get_bind()
    _seed_skills(conn)
    _seed_tests(conn)
    _seed_test_submissions(conn)
    _seed_categories(conn)


def downgrade() -> None:
    """Data migration — intentionally not reversed.

    The seeded rows may have been modified or referenced by real usage;
    deleting them on downgrade would be destructive. Re-running upgrade
    is a no-op for any table that still has rows.
    """
