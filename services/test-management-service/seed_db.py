#!/usr/bin/env python3
"""
Database seeding script for test-management-service.

Inserts a handful of demo users (with bcrypt password hashes) and demo
tests/skills/questions into the shared Postgres instance used by
user-service and test-management-service.
"""

import os
from datetime import datetime, timedelta

import psycopg2
from passlib.context import CryptContext
from psycopg2.extras import execute_values

# All seeded users share this password — local dev convenience only.
DEV_PASSWORD = "password123"
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEV_PASSWORD_HASH = _pwd_context.hash(DEV_PASSWORD)


def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USERNAME', 'root'),
        password=os.getenv('DB_PASSWORD', 'root'),
        dbname=os.getenv('DB_NAME', 'eval_ai_dev')
    )

def seed_users(conn):
    """Create mock users"""
    print("Seeding users...")

    cur = conn.cursor()

    # Check if users already exist
    cur.execute("SELECT COUNT(*) FROM users;")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"✅ Users table already has {count} users, skipping...")
        cur.close()
        return

    users_data = [
        # (email, full_name, first_name, last_name, role, organization_id)
        # Mock trainers
        ('trainer1@revature.com', 'John Trainer', 'John', 'Trainer', 'TRAINER', None),
        ('trainer2@revature.com', 'Sarah Instructor', 'Sarah', 'Instructor', 'TRAINER', None),
        # Mock participants
        ('student1@revature.com', 'Alice Johnson', 'Alice', 'Johnson', 'PARTICIPANT', None),
        ('student2@revature.com', 'Bob Smith', 'Bob', 'Smith', 'PARTICIPANT', None),
        ('student3@revature.com', 'Carol Davis', 'Carol', 'Davis', 'PARTICIPANT', None),
        ('student4@revature.com', 'David Wilson', 'David', 'Wilson', 'PARTICIPANT', None),
        ('student5@revature.com', 'Eva Brown', 'Eva', 'Brown', 'PARTICIPANT', None),
    ]

    execute_values(
        cur,
        """
        INSERT INTO users (email, password_hash, full_name, first_name, last_name, role, organization_id, is_active, created_at, updated_at)
        VALUES %s
        """,
        [
            (u[0], DEV_PASSWORD_HASH, u[1], u[2], u[3], u[4], u[5], True, datetime.utcnow(), datetime.utcnow())
            for u in users_data
        ]
    )

    conn.commit()
    cur.close()
    print(f"✅ Created {len(users_data)} users (shared dev password: {DEV_PASSWORD!r})")

def seed_tests(conn):
    """Create mock tests"""
    print("Seeding tests...")

    cur = conn.cursor()

    # Check if tests already exist
    cur.execute("SELECT COUNT(*) FROM tests;")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"✅ Tests table already has {count} tests, skipping...")
        cur.close()
        return

    # Get the first trainer
    cur.execute("SELECT id FROM users WHERE role = 'TRAINER' LIMIT 1;")
    trainer_id = cur.fetchone()[0]

    tests_data = [
        ('Java Fundamentals Quiz', 'QUIZ', 'Java Developer', 'Full Stack Java', '00:45:00', 20, trainer_id, True),
        ('Python Data Structures Quiz', 'QUIZ', 'Python Developer', 'Python Full Stack', '01:00:00', 25, trainer_id, True),
        ('System Design Interview', 'INTERVIEW', 'Senior Developer', 'System Design', '00:30:00', None, trainer_id, True),
        ('React Components Assessment', 'QUIZ', 'Frontend Developer', 'React Frontend', '00:40:00', 15, trainer_id, True),
        ('Behavioral Interview', 'INTERVIEW', 'Software Engineer', 'Soft Skills', '00:25:00', None, trainer_id, True),
        ('Advanced Java Quiz', 'QUIZ', 'Senior Java Developer', 'Full Stack Java', '00:50:00', 30, trainer_id, True),
    ]

    execute_values(
        cur,
        """
        INSERT INTO tests (name, test_type, role, curriculum, duration, number_of_questions, created_by_id, active, created_at, updated_at)
        VALUES %s
        """,
        [(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], datetime.utcnow(), datetime.utcnow()) for t in tests_data]
    )

    conn.commit()
    cur.close()
    print(f"✅ Created {len(tests_data)} tests")

def seed_skills(conn):
    """Create predefined skills"""
    print("Seeding skills...")

    cur = conn.cursor()

    # Check if skills already exist
    cur.execute("SELECT COUNT(*) FROM skills;")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"✅ Skills table already has {count} skills, skipping...")
        cur.close()
        return

    # Comprehensive skills list organized by category
    skills_data = [
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

    execute_values(
        cur,
        """
        INSERT INTO skills (name, description)
        VALUES %s
        """,
        [(s[0], s[1]) for s in skills_data]
    )

    conn.commit()
    cur.close()
    print(f"✅ Created {len(skills_data)} skills")

def seed_test_submissions(conn):
    """Create mock test submissions"""
    print("Seeding test submissions...")

    cur = conn.cursor()

    # Check if submissions already exist
    cur.execute("SELECT COUNT(*) FROM test_submissions;")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"✅ Test submissions table already has {count} submissions, skipping...")
        cur.close()
        return

    # Get tests and participant users
    cur.execute("SELECT id FROM tests;")
    test_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM users WHERE role = 'PARTICIPANT';")
    participant_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM users WHERE role = 'TRAINER' LIMIT 1;")
    trainer_id = cur.fetchone()[0]

    if not test_ids or not participant_ids:
        print("❌ Missing tests or participants!")
        cur.close()
        return

    submissions_data = []
    now = datetime.utcnow()

    for test_id in test_ids:
        for i, participant_id in enumerate(participant_ids):
            # Vary the status and scores
            if i == 0:  # First participant - completed
                status = 'COMPLETED'
                ai_score = 85
                final_score = 85
                started_at = now - timedelta(days=2)
                submitted_at = started_at + timedelta(minutes=30)
            elif i == 1:  # Second participant - in progress
                status = 'IN_PROGRESS'
                ai_score = None
                final_score = None
                started_at = now - timedelta(hours=1)
                submitted_at = None
            elif i == 2:  # Third participant - completed
                status = 'COMPLETED'
                ai_score = 92
                final_score = 92
                started_at = now - timedelta(days=1)
                submitted_at = started_at + timedelta(minutes=25)
            else:  # Others - assigned
                status = 'ASSIGNED'
                ai_score = None
                final_score = None
                started_at = None
                submitted_at = None

            feedback = f"Good performance" if status == 'COMPLETED' else None

            submissions_data.append((
                test_id,
                participant_id,
                trainer_id,
                now - timedelta(days=3),
                now + timedelta(days=7),
                status,
                started_at,
                submitted_at,
                ai_score,
                final_score,
                feedback,
                now,
                now
            ))

    execute_values(
        cur,
        """
        INSERT INTO test_submissions
        (test_id, user_id, assigned_by_id, assigned_at, due_date, status, started_at, submitted_at,
         ai_score, final_score, feedback, created_at, updated_at)
        VALUES %s
        """,
        submissions_data
    )

    conn.commit()
    cur.close()
    print(f"✅ Created {len(submissions_data)} test submissions")

def main():
    """Main seeding function"""
    print("🌱 Starting database seeding...")

    try:
        conn = get_db_connection()

        # Seed data in order
        seed_users(conn)
        seed_tests(conn)
        seed_skills(conn)
        seed_test_submissions(conn)

        # Print summary
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'TRAINER';")
        trainer_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'PARTICIPANT';")
        participant_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM tests;")
        test_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM skills;")
        skills_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM test_submissions;")
        submission_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM test_submissions WHERE status = 'COMPLETED';")
        completed_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM test_submissions WHERE status = 'IN_PROGRESS';")
        in_progress_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM test_submissions WHERE status = 'ASSIGNED';")
        assigned_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        print("\n🎉 Database seeding completed successfully!")
        print("\n📊 Summary:")
        print(f"  - Users: {trainer_count + participant_count} ({trainer_count} trainers, {participant_count} participants)")
        print(f"  - Tests: {test_count}")
        print(f"  - Skills: {skills_count}")
        print(f"  - Test Submissions: {submission_count}")
        print(f"    • Completed: {completed_count}")
        print(f"    • In Progress: {in_progress_count}")
        print(f"    • Assigned: {assigned_count}")

        print(f"\n🔑 Dev credentials: any seeded user / password = {DEV_PASSWORD!r}")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()

