"""The skill list and the code that finds skills in text.

Each skill is (name, kind, aliases).
- name: the label shown on the site.
- kind: language, framework, tool, cloud, data, hardware, robotics, concept or business.
- aliases: other ways people write it. The name itself is always matched too.

Most skills match without caring about upper or lower case.
Skills in CASE_SENSITIVE only match the exact spelling, because their lowercase
form is a normal word ("react to", "excel at", "unity", "spring 2027").
Skills in LIST_ONLY are short names that also appear in normal text ("Go", "C", "R").
They only match next to a comma, slash or "and", like "Python, Go, Rust".
"""

import re

SKILLS = [
    # Languages
    ("Python", "language", ["python3"]),
    ("Java", "language", []),
    ("JavaScript", "language", ["JS", "ECMAScript"]),
    ("TypeScript", "language", []),
    ("C++", "language", ["CPP", "C/C++"]),
    ("C#", "language", ["C Sharp", ".NET C#"]),
    ("C", "language", ["C/C++", "embedded C", "ANSI C", "C programming"]),
    ("Go", "language", ["Golang"]),
    ("Rust", "language", []),
    ("Kotlin", "language", []),
    ("Swift", "language", []),
    ("Ruby", "language", []),
    ("PHP", "language", []),
    ("Scala", "language", []),
    ("R", "language", ["RStudio", "R programming"]),
    ("MATLAB", "language", []),
    ("SQL", "language", []),
    ("Bash", "language", ["shell scripting", "shell scripts", "Bash scripting"]),
    ("Perl", "language", []),
    ("Haskell", "language", []),
    ("OCaml", "language", []),
    ("Julia", "language", []),
    ("Lua", "language", []),
    ("Assembly Language", "language", ["x86 assembly", "ARM assembly"]),
    ("Verilog", "language", ["SystemVerilog"]),
    ("VHDL", "language", []),
    ("Solidity", "language", []),
    ("Dart", "language", []),

    # Web and app frameworks
    ("React", "framework", ["React.js", "ReactJS"]),
    ("React Native", "framework", []),
    ("Next.js", "framework", ["NextJS"]),
    ("Angular", "framework", ["AngularJS"]),
    ("Vue", "framework", ["Vue.js", "VueJS"]),
    ("Svelte", "framework", []),
    ("Node.js", "framework", ["NodeJS", "Node"]),
    ("Express", "framework", ["Express.js", "ExpressJS"]),
    ("Django", "framework", []),
    ("Flask", "framework", []),
    ("FastAPI", "framework", []),
    ("Spring Boot", "framework", ["Spring Framework"]),
    ("Ruby on Rails", "framework", ["Rails"]),
    (".NET", "framework", ["ASP.NET", "dotnet", ".NET Core"]),
    ("Flutter", "framework", []),
    ("Tailwind CSS", "framework", ["Tailwind"]),
    ("Redux", "framework", []),
    ("HTML", "framework", ["HTML5"]),
    ("CSS", "framework", ["CSS3", "Sass", "SCSS"]),
    ("GraphQL", "framework", []),
    ("REST APIs", "concept", ["REST", "RESTful", "REST API"]),
    ("gRPC", "framework", []),
    ("iOS", "framework", ["iOS development"]),
    ("Android", "framework", ["Android development"]),
    ("Unity", "framework", []),
    ("Unreal Engine", "framework", ["Unreal"]),

    # Machine learning and data
    ("Machine Learning", "concept", ["ML"]),
    ("Deep Learning", "concept", []),
    ("NLP", "concept", ["natural language processing"]),
    ("Computer Vision", "concept", []),
    ("LLMs", "concept", ["LLM", "large language models", "large language model"]),
    ("Reinforcement Learning", "concept", []),
    ("PyTorch", "data", []),
    ("TensorFlow", "data", []),
    ("JAX", "data", []),
    ("scikit-learn", "data", ["sklearn", "scikit learn"]),
    ("Keras", "data", []),
    ("Hugging Face", "data", ["HuggingFace", "Transformers library"]),
    ("pandas", "data", []),
    ("NumPy", "data", []),
    ("SciPy", "data", []),
    ("OpenCV", "data", []),
    ("CUDA", "data", []),
    ("Spark", "data", ["Apache Spark", "PySpark"]),
    ("Hadoop", "data", []),
    ("Kafka", "data", ["Apache Kafka"]),
    ("Airflow", "data", ["Apache Airflow"]),
    ("dbt", "data", []),
    ("Snowflake", "data", []),
    ("Databricks", "data", []),
    ("Tableau", "data", []),
    ("Power BI", "data", ["PowerBI"]),
    ("Excel", "data", ["Microsoft Excel", "MS Excel"]),
    ("Statistics", "concept", ["statistical analysis", "statistical modeling"]),
    ("Data Analysis", "concept", ["data analytics"]),
    ("Data Visualization", "concept", []),
    ("A/B Testing", "concept", ["AB testing"]),
    ("ETL", "concept", ["data pipelines", "data pipeline"]),

    # Databases
    ("PostgreSQL", "tool", ["Postgres"]),
    ("MySQL", "tool", []),
    ("MongoDB", "tool", ["Mongo"]),
    ("Redis", "tool", []),
    ("SQLite", "tool", []),
    ("DynamoDB", "tool", []),
    ("Cassandra", "tool", []),
    ("Elasticsearch", "tool", ["Elastic Search", "OpenSearch"]),
    ("BigQuery", "tool", []),
    ("NoSQL", "concept", []),

    # Cloud and DevOps
    ("AWS", "cloud", ["Amazon Web Services", "EC2", "S3", "AWS Lambda"]),
    ("Azure", "cloud", ["Microsoft Azure"]),
    ("GCP", "cloud", ["Google Cloud", "Google Cloud Platform"]),
    ("Docker", "cloud", ["containerization"]),
    ("Kubernetes", "cloud", ["K8s"]),
    ("Terraform", "cloud", []),
    ("CI/CD", "cloud", ["continuous integration", "continuous deployment"]),
    ("Jenkins", "cloud", []),
    ("GitHub Actions", "cloud", []),
    ("Ansible", "cloud", []),
    ("Linux", "tool", ["Unix"]),
    ("Git", "tool", ["version control"]),
    ("Jira", "tool", []),
    ("Figma", "tool", []),

    # Computer science concepts
    ("Data Structures", "concept", []),
    ("Algorithms", "concept", []),
    ("Object-Oriented Programming", "concept", ["OOP", "object oriented programming", "object-oriented design"]),
    ("Distributed Systems", "concept", []),
    ("Operating Systems", "concept", []),
    ("Computer Networking", "concept", ["network protocols", "TCP/IP"]),
    ("System Design", "concept", []),
    ("Microservices", "concept", []),
    ("Multithreading", "concept", ["concurrency", "multi-threading", "parallel programming"]),
    ("Compilers", "concept", []),
    ("Cybersecurity", "concept", ["security engineering", "information security", "application security"]),
    ("Cryptography", "concept", []),
    ("Testing", "concept", ["unit testing", "test automation", "automated testing"]),
    ("Agile", "concept", ["Scrum"]),

    # Hardware and electrical
    ("Embedded Systems", "hardware", ["embedded software", "firmware"]),
    ("RTOS", "hardware", ["FreeRTOS", "real-time operating system"]),
    ("FPGA", "hardware", []),
    ("ASIC", "hardware", []),
    ("PCB Design", "hardware", ["PCB", "printed circuit board"]),
    ("Circuit Design", "hardware", ["circuit analysis", "analog design", "digital design"]),
    ("Signal Processing", "hardware", ["DSP", "digital signal processing"]),
    ("RF", "hardware", ["radio frequency"]),
    ("Power Electronics", "hardware", []),
    ("Altium", "hardware", ["Altium Designer"]),
    ("Cadence", "hardware", []),
    ("SPICE", "hardware", ["LTspice"]),
    ("Arduino", "hardware", []),
    ("Raspberry Pi", "hardware", []),
    ("Microcontrollers", "hardware", ["microcontroller", "STM32", "MCU"]),
    ("Oscilloscope", "hardware", ["oscilloscopes"]),

    # Mechanical and robotics
    ("ROS", "robotics", ["ROS2", "ROS 2", "Robot Operating System"]),
    ("Robotics", "robotics", []),
    ("Control Systems", "robotics", ["control theory", "feedback control", "controls engineering"]),
    ("PID Control", "robotics", ["PID"]),
    ("Kalman Filter", "robotics", ["Kalman filtering", "sensor fusion"]),
    ("SLAM", "robotics", []),
    ("Motion Planning", "robotics", ["path planning"]),
    ("CAD", "robotics", ["computer-aided design"]),
    ("SolidWorks", "robotics", []),
    ("Onshape", "robotics", []),
    ("Fusion 360", "robotics", []),
    ("AutoCAD", "robotics", []),
    ("CATIA", "robotics", []),
    ("Siemens NX", "robotics", []),
    ("Simulink", "robotics", []),
    ("LabVIEW", "robotics", []),
    ("FEA", "robotics", ["finite element analysis", "ANSYS"]),
    ("CFD", "robotics", ["computational fluid dynamics"]),
    ("3D Printing", "robotics", ["additive manufacturing"]),
    ("CNC", "robotics", ["CNC machining"]),
    ("GD&T", "robotics", []),

    # Quant and business
    ("Probability", "concept", []),
    ("Linear Algebra", "concept", []),
    ("Mathematical Optimization", "concept", ["convex optimization", "linear programming"]),
    ("Time Series", "concept", ["time-series"]),
    ("Financial Modeling", "business", ["financial modelling"]),
    ("Product Management", "business", []),
    ("User Research", "business", ["UX research"]),
    ("UI/UX Design", "business", ["UX design", "UI design", "UX/UI"]),
]

# Only match these with the exact spelling.
CASE_SENSITIVE = {
    "React", "Unity", "Excel", "Swift", "Rust", "Spark", "Express", "Node",
    "Julia", "Ruby", "Dart", "Agile", "Testing", "Cadence", "Snowflake",
    "RF", "JS", "ML", "S3", "EC2", "Lambda", "Mongo", "Unix", "Rails", "REST",
    "Scrum", "PID", "Unreal", "CAD", "MCU", "PCB", "ASIC", "JAX", "dbt",
}

# Words that are also normal words in course descriptions ("a flask", "airflow",
# "solidity", "spice"). Only the exact spelling counts.
CASE_SENSITIVE |= {"Angular", "AngularJS", "Flask", "Airflow", "Solidity", "Tableau", "SPICE"}

# Short names that are only skills in a list, like "Python, Go, Rust".
LIST_ONLY = {"Go", "C", "R"}

# A skill does not count when one of these words comes right after it.
# "Angular momentum" is physics, not the Angular framework.
NOT_FOLLOWED_BY = {
    "Angular": r"\s+(?:momentum|velocit|acceleration|frequenc|displacement|distribution|resolution|motion"
    r"|speed|size|diameter|dependence|correlation|variable|width|position|coordinate)",
}

# Skills we never tag on courses. In course calendars these are people and myths
# (Franz Kafka, Cassandra) or physics (airflow), not the data tools.
NOT_ON_COURSES = {"Kafka", "Cassandra", "Airflow"}

# Characters that count as part of a word, so "Java" does not match "JavaScript".
_EDGE_BEFORE = r"(?<![A-Za-z0-9+#])"
_EDGE_AFTER = r"(?![A-Za-z0-9+#])"
# A list separator: comma, slash, "and", "or", or brackets.
_SEP = r"(?:,|/|\(|\)|\band\b|\bor\b|;)"


def _pattern(alias, name):
    body = re.escape(alias)
    if alias in LIST_ONLY:
        # Must touch a separator on at least one side: "Python, Go" or "Go/Rust".
        # A dash also blocks it, so "C-suite" and "Go-to-market" do not count.
        before, after = r"(?<![A-Za-z0-9+#-])", r"(?![A-Za-z0-9+#-])"
        return re.compile(rf"(?:{_SEP}\s*{body}{after}|{before}{body}\s*{_SEP})")
    flags = 0 if alias in CASE_SENSITIVE else re.IGNORECASE
    not_after = f"(?!{NOT_FOLLOWED_BY[name]})" if name in NOT_FOLLOWED_BY else ""
    return re.compile(rf"{_EDGE_BEFORE}{body}{_EDGE_AFTER}{not_after}", flags)


# Build every pattern once, when the file is imported.
MATCHERS = [
    (name, [_pattern(a, name) for a in [name, *aliases]]) for name, _kind, aliases in SKILLS
]


def find_skills(text, course=False):
    """Return the sorted list of skill names mentioned in the text.
    Set course=True for course descriptions, which skip NOT_ON_COURSES."""
    # Drop trademark marks, so "Microsoft(R)" does not count as the R language.
    text = (text or "").replace("(R)", " ").replace("(C)", " ")
    return sorted(
        name
        for name, patterns in MATCHERS
        if not (course and name in NOT_ON_COURSES) and any(p.search(text) for p in patterns)
    )


if __name__ == "__main__":
    print(len(SKILLS), "skills")
    samples = [
        "Experience with Python, Go, and Rust. Familiar with React and Node.js.",
        "You will react to feedback and excel at teamwork. Spring 2027 internship.",
        "Strong C/C++ skills, embedded C on STM32 microcontrollers, FreeRTOS.",
        "Go above and beyond. Series C startup. R&D team.",
        "Use PyTorch, scikit-learn and SQL. Knowledge of JavaScript and TypeScript.",
        "ROS2, SLAM, Kalman filtering, SolidWorks and CAD design.",
        "Proficient in R, Python and Excel for statistical analysis.",
        "Active TS/SCI clearance. Go-to-market plans for the C-suite.",
        "Microsoft(R) Office. Mechanical assembly of parts. Internal controls.",
        "Networking events and shipping containers. Cost optimization.",
    ]
    for s in samples:
        print(find_skills(s), "<-", s)
