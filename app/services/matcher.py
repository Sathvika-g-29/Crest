from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchReport, SkillMatch


model = SentenceTransformer("all-MiniLM-L6-v2")


def calculate_similarity(text1: str, text2: str) -> float:
    embeddings = model.encode([text1, text2])

    similarity = cosine_similarity(
        [embeddings[0]],
        [embeddings[1]]
    )[0][0]

    return round(float(similarity), 3)


def normalize(text: str) -> str:
    return (
        text.lower()
        .replace("-", " ")
        .replace("/", " ")
        .strip()
    )


def build_candidate_evidence(
    candidate: CandidateProfile
) -> list[tuple[str, str]]:

    evidence = []

    # Direct resume skills
    for skill in candidate.skills:
        evidence.append(
            (skill.name, skill.evidence)
        )

    # Technologies used in projects
    for project in candidate.projects:
        for technology in project.technologies:
            evidence.append(
                (
                    technology,
                    f"{project.name}: {project.description}"
                )
            )

    # Project descriptions
    for project in candidate.projects:
        evidence.append(
            (
                project.name,
                project.description
            )
        )

    # Experience
    for experience in candidate.experience:
        evidence.append(
            (
                experience.role,
                experience.description
            )
        )

    return evidence


def match_candidate_to_job(
    candidate: CandidateProfile,
    job: JobProfile
) -> MatchReport:

    candidate_evidence = build_candidate_evidence(candidate)

    matched_skills = []
    missing_skills = []

    # Keep track of whether each requirement is required or preferred
    requirements = (
        [
            ("required", skill)
            for skill in job.required_skills
        ]
        +
        [
            ("preferred", skill)
            for skill in job.preferred_skills
        ]
    )

    for requirement_type, requirement in requirements:

        requirement_name = requirement.name
        requirement_category = requirement.category
        requirement_specificity = requirement.specificity

        best_evidence = None
        best_similarity = 0.0
        best_status = None

        for evidence_name, evidence_text in candidate_evidence:

            # Find the corresponding structured candidate skill
            candidate_skill = next(
                (
                    skill
                    for skill in candidate.skills
                    if normalize(skill.name) == normalize(evidence_name)
                ),
                None
            )

            # ------------------------------------------------
            # 1. Exact match
            # ------------------------------------------------
            if normalize(requirement_name) == normalize(evidence_name):

                best_evidence = evidence_text
                best_similarity = 1.0
                best_status = "exact_match"

                break

            # ------------------------------------------------
            # 2. Category-level match
            #
            # Example:
            # Job requirement: vector databases
            # Resume skill: ChromaDB
            #
            # Both:
            # category = vector_database
            #
            # This is a related match, not an exact match.
            # ------------------------------------------------
            if (
                requirement_specificity == "technology_category"
                and candidate_skill
                and candidate_skill.category == requirement_category
                and candidate_skill.specificity == "specific_technology"
            ):

                best_evidence = evidence_text
                best_similarity = 1.0
                best_status = "related_match"

                continue

            # ------------------------------------------------
            # 3. Semantic matching
            #
            # Only non-specific requirements can use semantic
            # similarity.
            #
            # This prevents:
            #
            # FastAPI → Django
            #
            # from being considered a match just because
            # both are frameworks.
            # ------------------------------------------------
            if requirement_specificity != "specific_technology":

                similarity = calculate_similarity(
                    requirement_name,
                    evidence_name
                )

                if similarity > best_similarity:

                    best_similarity = similarity
                    best_evidence = evidence_text
                    best_status = "semantic_match"

        # ------------------------------------------------
        # Final decision
        # ------------------------------------------------

        if best_status == "exact_match":

            matched_skills.append(
                SkillMatch(
                    skill=requirement_name,
                    job_requirement=requirement_name,
                    requirement_type=requirement_type,
                    resume_evidence=best_evidence,
                    similarity=best_similarity,
                    status="exact_match"
                )
            )

        elif best_status == "related_match":

            matched_skills.append(
                SkillMatch(
                    skill=requirement_name,
                    job_requirement=requirement_name,
                    requirement_type=requirement_type,
                    resume_evidence=best_evidence,
                    similarity=best_similarity,
                    status="related_match"
                )
            )

        elif (
            best_status == "semantic_match"
            and best_similarity >= 0.70
        ):

            matched_skills.append(
                SkillMatch(
                    skill=requirement_name,
                    job_requirement=requirement_name,
                    requirement_type=requirement_type,
                    resume_evidence=best_evidence,
                    similarity=best_similarity,
                    status="semantic_match"
                )
            )

        else:

            missing_skills.append(requirement_name)

    # ------------------------------------------------
    # Calculate resume-to-job coverage
    # ------------------------------------------------

    total_requirements = len(requirements)
    matched_count = len(matched_skills)

    match_percentage = (
        round(
            (matched_count / total_requirements) * 100,
            2
        )
        if total_requirements > 0
        else 0.0
    )

    # ------------------------------------------------
    # Final report
    # ------------------------------------------------

    return MatchReport(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        match_percentage=match_percentage
    )