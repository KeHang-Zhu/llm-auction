"""
Deferred Acceptance (DA) Simulation with LLMs

This module implements Deferred Acceptance matching mechanisms using LLM agents.
Supports both direct revelation (full ranking submission) and OSP (sequential local queries).

Architecture mirrors util_plan.py (auction simulation).
"""

import random
import json
import os
import re
from edsl import Model, Survey, Cache
from edsl.questions import QuestionRank, QuestionMultipleChoice, QuestionFreeText
from edsl.prompts import Prompt

current_script_path = os.path.dirname(os.path.abspath(__file__))
prompt_dir = os.path.join(current_script_path, '../Prompt/')


def save_json(data, filename, directory):
    """Save data to a JSON file in the specified directory."""
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    return file_path


class Rule_DA:
    """
    Defines DA mechanism rules and renders Jinja2 templates.
    """
    def __init__(self, mechanism_type, intervention_type="baseline",
                 special_name=None, templates_dir=None, common_range=[40, 70],
                 private_range=20, global_ranking_strategy="average"):
        """
        Initialize DA rule.

        Args:
            mechanism_type: "direct" or "osp"
            intervention_type: Cognitive intervention (e.g., "baseline", "axis1_enumerate")
            special_name: Override template filename
            templates_dir: Path to rule_template/DA/
            common_range: Range for common value component
            private_range: Range for private value component
            global_ranking_strategy: Strategy for computing global ranking
                - "average": Based on average values
                - "fixed": Fixed ranking for all experiments
                - "random": Random ranking
                - "misleading": Reverse of average (for experiments)
        """
        self.mechanism_type = mechanism_type
        self.intervention_type = intervention_type
        self.special_name = special_name
        self.common_range = common_range
        self.private_range = private_range
        self.global_ranking_strategy = global_ranking_strategy
        self.number_students = 4
        self.number_schools = 4

        # Resolve templates directory
        if templates_dir is None:
            self.templates_dir = os.path.join(current_script_path, '../rule_template/DA/')
        elif not os.path.isabs(templates_dir):
            self.templates_dir = os.path.join(current_script_path, '..', templates_dir)
        else:
            self.templates_dir = templates_dir

        # Load template
        self.rule_explanation = self._load_template()

    def _load_template(self):
        """Load appropriate template file based on mechanism type."""
        if self.special_name:
            template_file = self.special_name
        else:
            # Default templates
            if self.mechanism_type == "direct":
                if self.intervention_type == "baseline":
                    template_file = "da_direct_traditional.txt"
                else:
                    template_file = f"{self.intervention_type}.txt"
            elif self.mechanism_type == "osp":
                template_file = "da_osp_choice.txt"
            else:
                raise ValueError(f"Unknown mechanism_type: {self.mechanism_type}")

        template_path = os.path.join(self.templates_dir, template_file)
        template_string = Prompt.from_txt(template_path)

        # Return template string (will be rendered later with student-specific data)
        return template_string

    def describe(self):
        """Print mechanism description."""
        print(f"DA Mechanism Type: {self.mechanism_type}")
        print(f"Intervention Type: {self.intervention_type}")
        print(f"Number of Students: {self.number_students}")
        print(f"Number of Schools: {self.number_schools}")


class Student:
    """
    Represents a student agent in the DA matching mechanism.
    Parallel to Bidder class in auction simulation.
    """
    def __init__(self, value_dict, priority_dict, name, rule):
        """
        Initialize student.

        Args:
            value_dict: Dict[school, value] - values for each school
            priority_dict: Dict[school, priority_rank] - priorities at each school
            name: Student name ("A", "B", "C", "D")
            rule: Rule_DA instance
        """
        self.name = f"Student {name}"
        self.rule = rule
        self.values = value_dict  # {"w": 85, "x": 72, "y": 90, "z": 65}
        self.priorities = priority_dict  # {"w": 1, "x": 2, "y": 1, "z": 2}

        # Outcomes
        self.submitted_ranking = None  # For direct: ["w", "x", "y", "z"]
        self.osp_choices = []  # For OSP: sequential choices
        self.matched_school = None  # Final match
        self.utility = 0  # Final utility
        self.reasoning = ""  # LLM reasoning

    def get_utility(self, matched_school):
        """Return value for matched school or 0 if unmatched."""
        if matched_school is None:
            return 0
        return self.values.get(matched_school, 0)

    def __repr__(self):
        return f"{self.name}(values={self.values}, matched={self.matched_school})"


class DA_Direct:
    """
    Implements direct revelation mechanism (submit full ranking once).
    Uses QuestionRank for parallel querying of all students.
    """
    def __init__(self, students, rule, model, cache=None, global_ranking=None):
        """
        Initialize direct revelation mechanism.

        Args:
            students: List of Student objects
            rule: Rule_DA instance
            model: EDSL Model instance
            cache: EDSL Cache instance
            global_ranking: Optional global ranking string for social information
        """
        self.students = students
        self.rule = rule
        self.model = model
        self.cache = cache
        self.global_ranking = global_ranking or "w > x > y > z"  # Default fallback
        self.da_trace = []  # Trace of DA algorithm execution

    def run(self):
        """
        Main execution: parallel Survey with QuestionFreeText to collect reasoning.

        Returns:
            Dict with 'rankings', 'reasoning', 'matches', 'da_trace'
        """
        print("Running DA Direct Mechanism...")

        # STEP 1: Build prompts for all students
        student_prompts = []
        for student in self.students:
            prompt = self._build_student_prompt(student)
            student_prompts.append((student, prompt))

        # STEP 2: Create parallel Survey with QuestionFreeText (to collect reasoning)
        questions = []
        for student, prompt in student_prompts:
            q_freetext = QuestionFreeText(
                question_name=f"q_reason_{student.name.replace(' ', '_')}",
                question_text=prompt
            )
            questions.append(q_freetext)

        # STEP 3: Execute parallel LLM calls
        survey = Survey(questions=questions)
        result = survey.by(self.model).run(cache=self.cache)

        # STEP 4: Parse reasoning and rankings with retry logic
        submitted_rankings = {}
        reasoning_dict = {}

        for i, (student, prompt) in enumerate(student_prompts):
            question_name = f"q_reason_{student.name.replace(' ', '_')}"
            response = result.select(question_name).to_list()[0]

            # Parse reasoning and ranking with retries
            reason, ranking = self._parse_and_validate_response(response, student, prompt)

            submitted_rankings[student.name] = ranking
            reasoning_dict[student.name] = reason

            student.submitted_ranking = ranking
            student.reasoning = reason

            print(f"{student.name} submitted ranking: {ranking}")

        # STEP 5: Compute truthfulness
        truthfulness = self._compute_truthfulness()

        # STEP 6: Run DA algorithm
        matches = self._run_da_algorithm(submitted_rankings)

        # STEP 7: Record outcomes
        self._record_outcomes(matches)

        return {
            'rankings': submitted_rankings,
            'reasoning': reasoning_dict,
            'truthfulness': truthfulness,
            'matches': matches,
            'da_trace': self.da_trace
        }

    def _build_student_prompt(self, student):
        """Render template with student's preference order and priorities."""
        # Compute preference order (sorted by value, descending)
        sorted_schools = sorted(student.values.items(), key=lambda x: x[1], reverse=True)
        preference_order = " > ".join([school for school, _ in sorted_schools])
        # Example: "x > y > w > z"

        # Render main mechanism explanation template
        main_prompt = self.rule.rule_explanation.render({
            "student_id": student.name.split()[-1],  # "A", "B", etc.
            "preference_order": preference_order,  # Ordinal preferences only
            "pw": student.priorities["w"],
            "px": student.priorities["x"],
            "py": student.priorities["y"],
            "pz": student.priorities["z"],
            "global_ranking": self.global_ranking  # Add global ranking
        })

        # Load and append da_ask.txt (reasoning instruction)
        da_ask_path = os.path.join(prompt_dir, 'da_ask.txt')
        if os.path.exists(da_ask_path):
            with open(da_ask_path, 'r') as f:
                da_ask_content = f.read()
            full_prompt = str(main_prompt) + "\n\n" + da_ask_content
        else:
            # Fallback if da_ask.txt doesn't exist
            full_prompt = str(main_prompt)

        return full_prompt

    def _parse_and_validate_response(self, initial_response, student, full_prompt):
        """
        Parse <REASON> and <DECISION> tags with 3-attempt retry logic.

        Args:
            initial_response: LLM response with <REASON> and <DECISION> tags
            student: Student object
            full_prompt: Full prompt text for retry

        Returns:
            Tuple[str, List[str]]: (reason, ranking)

        Raises:
            RuntimeError: If parsing fails after 3 attempts
        """
        response = initial_response

        for attempt in range(3):
            try:
                # Parse REASON and DECISION tags
                reason, decision_text = self._parse_reason_decision(response)

                # Use gpt-4o-mini to extract ranking from decision text
                ranking = self._extract_ranking_with_model(decision_text, student)

                if self._is_valid_ranking(ranking):
                    return reason, ranking
                raise ValueError("Invalid ranking: missing schools or duplicates")

            except Exception as e:
                print(f"{student.name} parsing error (attempt {attempt+1}/3): {e}")

                if attempt < 2:
                    # Retry with error message
                    q_retry = QuestionFreeText(
                        question_name="q_reason_retry",
                        question_text=full_prompt + f"\n\nError: {e}. You MUST use the format:\n<REASON>Your reasoning here</REASON>\n<DECISION>Ranking: w > x > y > z</DECISION>"
                    )
                    survey = Survey(questions=[q_retry])
                    result = survey.by(self.model).run(cache=self.cache)
                    response = result.select("q_reason_retry").to_list()[0]

        raise RuntimeError(f"{student.name} failed to parse response after 3 attempts")

    def _parse_reason_decision(self, text):
        """
        Parse <REASON> and <DECISION> tags from LLM response.

        Args:
            text: LLM response text

        Returns:
            Tuple[str, str]: (reason, decision_text)

        Raises:
            ValueError: If tags not found
        """
        # Parse REASON
        reason_pattern = r"<REASON>(.*?)</REASON>"
        reason_match = re.search(reason_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not reason_match:
            raise ValueError("REASON tag not found")
        reason = reason_match.group(1).strip()

        # Parse DECISION
        decision_pattern = r"<DECISION>(.*?)</DECISION>"
        decision_match = re.search(decision_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not decision_match:
            raise ValueError("DECISION tag not found")
        decision = decision_match.group(1).strip()

        return reason, decision

    def _extract_ranking_with_model(self, decision_text, student):
        """
        Use gpt-4o-mini to extract ranking from decision text.

        Args:
            decision_text: Text from <DECISION> tag
            student: Student object

        Returns:
            List[str]: Ranking ["w", "x", "y", "z"]
        """
        # First try direct parsing
        try:
            ranking = self._parse_ranking(decision_text)
            if self._is_valid_ranking(ranking):
                return ranking
        except:
            pass

        # If direct parsing fails, use gpt-4o-mini
        extraction_prompt = f"""
Extract the school ranking from the following decision text.
The student must rank 4 schools: w, x, y, z.

Decision text:
{decision_text}

Respond with ONLY the ranking in the format: w > x > y > z
Do NOT include any other text.
"""

        q_extract = QuestionFreeText(
            question_name="q_extract",
            question_text=extraction_prompt
        )
        survey = Survey(questions=[q_extract])

        # Use gpt-4o-mini for extraction
        extract_model = (Model("openai/gpt-4o-mini", temperature=0, service_name="open_router")
                         if os.environ.get("OPEN_ROUTER_API_KEY") and not os.environ.get("OPENAI_API_KEY")
                         else Model("gpt-4o-mini", temperature=0))  # route extraction via OpenRouter when only that key exists (2026-07-08)
        result = survey.by(extract_model).run()
        extracted = result.select("q_extract").to_list()[0]

        # Parse the extracted text
        ranking = self._parse_ranking(extracted)
        return ranking

    def _parse_and_validate_ranking(self, initial_response, student, full_prompt):
        """
        Parse ranking with 3-attempt retry logic.

        Args:
            initial_response: LLM response
            student: Student object
            full_prompt: Full prompt text for retry

        Returns:
            List[str]: Validated ranking ["w", "x", "y", "z"]

        Raises:
            RuntimeError: If parsing fails after 3 attempts
        """
        response = initial_response

        for attempt in range(3):
            try:
                ranking = self._parse_ranking(response)
                if self._is_valid_ranking(ranking):
                    return ranking
                raise ValueError("Invalid ranking: missing schools or duplicates")
            except Exception as e:
                print(f"{student.name} parsing error (attempt {attempt+1}/3): {e}")

                if attempt < 2:
                    # Retry with error message
                    q_retry = QuestionRank(
                        question_name="q_rank_retry",
                        question_text=full_prompt + f"\n\nError: {e}. You MUST follow the format: Ranking: <1st> > <2nd> > <3rd> > <4th>",
                        question_options=["w", "x", "y", "z"]
                    )
                    survey = Survey(questions=[q_retry])
                    result = survey.by(self.model).run(cache=self.cache)
                    response = result.select("q_rank_retry").to_list()[0]

        raise RuntimeError(f"{student.name} failed to parse ranking after 3 attempts")

    def _parse_ranking(self, response):
        """
        Parse ranking from QuestionRank response.

        Handles formats:
        - ["w", "x", "y", "z"] (list)
        - "Ranking: w > x > y > z" (text)
        - "w > x > y > z" (text)

        Returns:
            List[str]: ["w", "x", "y", "z"]
        """
        if isinstance(response, list):
            return [str(x).lower().strip() for x in response]

        # Parse text format
        text = str(response).lower()

        # Try "Ranking: w > x > y > z"
        pattern = r"ranking:\s*([w-z])\s*>\s*([w-z])\s*>\s*([w-z])\s*>\s*([w-z])"
        match = re.search(pattern, text)
        if match:
            return list(match.groups())

        # Try direct "w > x > y > z"
        pattern2 = r"([w-z])\s*>\s*([w-z])\s*>\s*([w-z])\s*>\s*([w-z])"
        match2 = re.search(pattern2, text)
        if match2:
            return list(match2.groups())

        # Try comma-separated "w, x, y, z"
        pattern3 = r"([w-z]),\s*([w-z]),\s*([w-z]),\s*([w-z])"
        match3 = re.search(pattern3, text)
        if match3:
            return list(match3.groups())

        raise ValueError(f"Could not parse ranking from: {response}")

    def _is_valid_ranking(self, ranking):
        """Validate ranking contains all schools exactly once."""
        if not isinstance(ranking, list) or len(ranking) != 4:
            return False
        schools = {"w", "x", "y", "z"}
        return set(ranking) == schools

    def _run_da_algorithm(self, submitted_rankings):
        """
        Run student-proposing Deferred Acceptance algorithm.

        Args:
            submitted_rankings: Dict[student_name, List[school]]

        Returns:
            Dict[student_name, Optional[school]]: Final matches
        """
        print("\nRunning DA Algorithm...")

        tentative_matches = {}  # {school: student_name}
        student_next_proposal = {s.name: 0 for s in self.students}
        unmatched = set(s.name for s in self.students)

        round_num = 0
        while unmatched:
            proposals = {}  # {school: [students]}

            # Each unmatched student proposes to next school on their list
            for student_name in list(unmatched):
                idx = student_next_proposal[student_name]
                ranking = submitted_rankings[student_name]

                if idx >= len(ranking):
                    # Student exhausted their list
                    unmatched.remove(student_name)
                    continue

                school = ranking[idx]
                student_next_proposal[student_name] += 1
                proposals.setdefault(school, []).append(student_name)

            if not proposals:
                break  # No more proposals possible

            # Each school keeps highest-priority proposer
            rejections = []
            for school, proposers in proposals.items():
                candidates = proposers[:]
                if school in tentative_matches:
                    candidates.append(tentative_matches[school])

                best = self._select_by_priority(school, candidates)

                # Track rejections
                for candidate in candidates:
                    if candidate != best:
                        rejections.append((candidate, school))
                        if candidate in proposers:
                            # Student was just rejected, remains unmatched
                            pass

                # Update tentative match
                if school in tentative_matches and tentative_matches[school] != best:
                    old_match = tentative_matches[school]
                    unmatched.add(old_match)

                tentative_matches[school] = best
                unmatched.discard(best)

            # Log this round
            self.da_trace.append({
                'round': round_num,
                'proposals': proposals.copy(),
                'tentative_matches': tentative_matches.copy(),
                'rejections': rejections
            })

            print(f"  Round {round_num}: {len(proposals)} proposals, {len(rejections)} rejections")
            round_num += 1

        # Convert school->student to student->school
        matches = {s.name: None for s in self.students}
        for school, student_name in tentative_matches.items():
            matches[student_name] = school

        print(f"\nDA Algorithm complete after {round_num} rounds")
        return matches

    def _select_by_priority(self, school, candidates):
        """
        Select student with highest priority at school.
        Lower priority number = higher priority (1 is best).

        Args:
            school: School name
            candidates: List of student names

        Returns:
            str: Best student name
        """
        best = None
        best_priority = float('inf')

        for student_name in candidates:
            student = next(s for s in self.students if s.name == student_name)
            priority = student.priorities[school]

            if priority < best_priority:
                best_priority = priority
                best = student_name

        return best

    def _compute_truthfulness(self):
        """
        Compute truthfulness for each student by comparing true preferences with submitted ranking.

        Returns:
            Dict[student_name, bool]: Truthfulness for each student
        """
        truthfulness = {}

        for student in self.students:
            # Compute true preference ranking from values (descending order)
            true_ranking = sorted(
                student.values.items(),
                key=lambda x: x[1],
                reverse=True
            )
            true_ranking = [school for school, _ in true_ranking]

            # Compare with submitted ranking
            submitted = student.submitted_ranking

            # Truthful if rankings match exactly
            is_truthful = (true_ranking == submitted)

            truthfulness[student.name] = is_truthful

            if not is_truthful:
                print(f"  {student.name} MISREPORTED:")
                print(f"    True preference: {' > '.join(true_ranking)}")
                print(f"    Submitted: {' > '.join(submitted)}")

        return truthfulness

    def _record_outcomes(self, matches):
        """Store outcomes in student objects."""
        for student in self.students:
            student.matched_school = matches[student.name]
            student.utility = student.get_utility(student.matched_school)
            print(f"{student.name}: matched to {student.matched_school}, utility={student.utility}")


class DA_OSP:
    """
    Implements OSP mechanism (sequential local queries).
    Uses QuestionMultipleChoice with dynamic available sets.
    """
    def __init__(self, students, rule, model, cache=None, global_ranking=None):
        """
        Initialize OSP mechanism.

        Args:
            students: List of Student objects
            rule: Rule_DA instance
            model: EDSL Model instance
            cache: EDSL Cache instance
            global_ranking: Optional global ranking string for social information
        """
        self.students = students
        self.rule = rule
        self.model = model
        self.cache = cache
        self.global_ranking = global_ranking or "w > x > y > z"  # Default fallback

        # State management
        self.available_sets = {}  # {student_name: set of schools}
        self.tentative_matches = {}  # {school: student_name}
        self.osp_round = 0
        self.osp_history = []

    def _get_top_priority_students(self, remaining_students, remaining_schools):
        """
        Find students who have the highest priority at some remaining school,
        among the remaining students.

        Args:
            remaining_students: Set[str] - unmatched student names
            remaining_schools: Set[str] - unassigned schools

        Returns:
            Set[str]: Students who have top priority (among remaining students)
                     at at least one remaining school
        """
        top_students = set()

        for school in remaining_schools:
            # Find the student with the highest priority at this school
            # among remaining students only
            best_priority = float('inf')
            best_student = None

            for student_name in remaining_students:
                student = next(s for s in self.students if s.name == student_name)
                priority = student.priorities[school]

                if priority < best_priority:
                    best_priority = priority
                    best_student = student_name

            if best_student:
                top_students.add(best_student)

        return top_students

    def _get_priority_one_schools(self, student, remaining_schools, remaining_students):
        """
        Find schools where student has the highest priority among remaining students.

        Args:
            student: Student object
            remaining_schools: Set[str] - unassigned schools
            remaining_students: Set[str] - unmatched student names

        Returns:
            List[str]: Schools where student has top priority among remaining students,
                      in alphabetical order
        """
        top_priority_schools = []

        for school in remaining_schools:
            # Check if this student has the best priority at this school
            # among all remaining students
            student_priority = student.priorities[school]
            has_top_priority = True

            for other_name in remaining_students:
                if other_name == student.name:
                    continue
                other = next(s for s in self.students if s.name == other_name)
                if other.priorities[school] < student_priority:
                    has_top_priority = False
                    break

            if has_top_priority:
                top_priority_schools.append(school)

        return sorted(top_priority_schools)  # Alphabetical order for deterministic tree

    def _ask_yes_no(self, student, candidate, fallback_set, remaining_set):
        """
        Ask yes/no question using da_osp_yesno_guaranteed.txt template.

        Args:
            student: Student object
            candidate: str - school being offered
            fallback_set: Set[str] - schools remaining if NO
            remaining_set: Set[str] - all currently remaining schools

        Returns:
            Tuple[bool, str]: (answer YES=True/NO=False, reasoning text)
        """
        # Compute preference order
        sorted_schools = sorted(student.values.items(), key=lambda x: x[1], reverse=True)
        preference_order = " > ".join([school for school, _ in sorted_schools])

        # Format sets as strings
        remaining_str = ", ".join(sorted(remaining_set))
        fallback_str = ", ".join(sorted(fallback_set))

        # Render yes/no template
        # Load the yes/no template from rule_template/DA/
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        template_path = os.path.join(project_root, 'rule_template', 'DA', 'da_osp_yesno_guaranteed.txt')
        with open(template_path, 'r') as f:
            template_content = f.read()

        from jinja2 import Template
        template = Template(template_content)

        prompt = template.render({
            "student_id": student.name.split()[-1],
            "remaining_set": remaining_str,
            "preference_order": preference_order,
            "pw": student.priorities["w"],
            "px": student.priorities["x"],
            "py": student.priorities["y"],
            "pz": student.priorities["z"],
            "global_ranking": self.global_ranking,
            "candidate": candidate,
            "fallback_set": fallback_str
        })

        # Query LLM with QuestionFreeText to collect reasoning
        q = QuestionFreeText(
            question_name=f"q_yesno_{student.name.replace(' ', '_')}_{candidate}",
            question_text=prompt
        )

        survey = Survey(questions=[q])
        result = survey.by(self.model).run(cache=self.cache)
        response = result.select(q.question_name).to_list()[0]

        # Extract reasoning from <REASON> tag
        reason_match = re.search(r'<REASON>(.*?)</REASON>', response, flags=re.IGNORECASE | re.DOTALL)
        if reason_match:
            reasoning = reason_match.group(1).strip()
        else:
            reasoning = response  # Use full response if no REASON tag

        # Parse YES/NO answer from <DECISION> tag or direct text
        # First try to find <DECISION> tag
        decision_match = re.search(r'<DECISION>(.*?)</DECISION>', response, flags=re.IGNORECASE | re.DOTALL)
        decision_text = decision_match.group(1) if decision_match else response

        # Look for "Answer: YES" or "Answer: NO" in decision text
        answer_match = re.search(r'Answer:\s*(YES|NO)', decision_text, flags=re.IGNORECASE)
        if not answer_match:
            # Try to find YES or NO in the decision text
            if 'YES' in decision_text.upper():
                answer = True
            elif 'NO' in decision_text.upper():
                answer = False
            else:
                print(f"Warning: Could not parse YES/NO from response, defaulting to NO")
                answer = False
        else:
            answer = (answer_match.group(1).upper() == 'YES')

        return answer, reasoning

    def _ask_pick_top(self, student, remaining_schools):
        """
        Ask student to pick top school from remaining set (for serial dictatorship or final picks).

        Args:
            student: Student object
            remaining_schools: Set[str] - available schools

        Returns:
            Tuple[str, str]: (chosen school, reasoning text)
        """
        # Load da_osp_choice.txt template directly (not self.rule.rule_explanation which is yes/no template)
        available_str = ", ".join(sorted(remaining_schools))

        # Compute preference order
        sorted_schools = sorted(student.values.items(), key=lambda x: x[1], reverse=True)
        preference_order = " > ".join([school for school, _ in sorted_schools])

        # Load choice template from rule_template/DA/
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        template_path = os.path.join(project_root, 'rule_template', 'DA', 'da_osp_choice.txt')
        with open(template_path, 'r') as f:
            template_content = f.read()

        from jinja2 import Template
        template = Template(template_content)

        # Render template
        prompt = template.render({
            "student_id": student.name.split()[-1],
            "available_set": available_str,
            "preference_order": preference_order,
            "pw": student.priorities["w"],
            "px": student.priorities["x"],
            "py": student.priorities["y"],
            "pz": student.priorities["z"],
            "global_ranking": self.global_ranking
        })

        # Query LLM
        q = QuestionFreeText(
            question_name=f"q_pick_{student.name.replace(' ', '_')}",
            question_text=prompt
        )

        survey = Survey(questions=[q])
        result = survey.by(self.model).run(cache=self.cache)
        response = result.select(q.question_name).to_list()[0]

        # Extract reasoning from <REASON> tag
        reason_match = re.search(r'<REASON>(.*?)</REASON>', response, flags=re.IGNORECASE | re.DOTALL)
        if reason_match:
            reasoning = reason_match.group(1).strip()
        else:
            reasoning = response

        # Parse choice from <DECISION> tag or full response
        # First try to find <DECISION> tag
        decision_match = re.search(r'<DECISION>(.*?)</DECISION>', response, flags=re.IGNORECASE | re.DOTALL)
        decision_text = decision_match.group(1) if decision_match else response

        # Try to extract choice using model-based extraction
        try:
            choice = self._extract_osp_choice_with_model(decision_text, student, remaining_schools)
        except Exception as e:
            # Fallback: simple regex
            print(f"Warning: Model extraction failed, using regex fallback: {e}")
            match = re.search(r'Choice:\s*([w-z])', decision_text, flags=re.IGNORECASE)
            if match:
                choice = match.group(1).lower()
            else:
                # Last resort: find first school mentioned
                for school in sorted(remaining_schools):
                    if school in decision_text.lower():
                        choice = school
                        break
                else:
                    raise ValueError(f"Could not parse choice from: {decision_text}")

        return choice, reasoning

    def run(self):
        """
        Run true OSP mechanism using Ashlagi-Gonczarowski decision tree.

        Returns:
            Dict with 'osp_tree_trace', 'matches', 'truthfulness'
        """
        print("Running True OSP Mechanism (Ashlagi-Gonczarowski tree)...")

        # Initialize state
        remaining_students = set(s.name for s in self.students)
        remaining_schools = {"w", "x", "y", "z"}
        matches = {s.name: None for s in self.students}
        self.osp_tree_trace = []  # Replace osp_history with tree trace

        # Run recursive OSP tree
        self._run_osp_tree(
            remaining_students,
            remaining_schools,
            matches,
            node_path=[]
        )

        # Record outcomes in student objects
        self._record_outcomes(matches)

        # Compute truthfulness
        truthfulness = self._compute_osp_truthfulness()

        # Calculate truthfulness rate
        truthful_count = sum(truthfulness.values())
        total_count = len(truthfulness)
        truthfulness_rate = truthful_count / total_count if total_count > 0 else 0

        return {
            'osp_tree_trace': self.osp_tree_trace,
            'matches': matches,
            'truthfulness': truthfulness,
            'truthfulness_rate': truthfulness_rate
        }

    def _run_osp_tree(self, remaining_students, remaining_schools, matches, node_path):
        """
        Recursive OSP tree following Ashlagi-Gonczarowski construction.

        Args:
            remaining_students: Set[str] - unmatched student names
            remaining_schools: Set[str] - unassigned schools
            matches: Dict[str, Optional[str]] - current matches (mutated in place)
            node_path: List[str] - path in tree (for logging)
        """
        # Base case: all matched or no schools left
        if not remaining_students or not remaining_schools:
            return

        # Identify top-priority students
        top_students = self._get_top_priority_students(
            remaining_students,
            remaining_schools
        )

        node_info = {
            'node_path': node_path.copy(),
            'remaining_students': sorted(remaining_students),
            'remaining_schools': sorted(remaining_schools),
            'top_students': sorted(top_students)
        }

        print(f"\nOSP Tree Node: {len(top_students)} top-priority students")
        print(f"  Remaining students: {sorted(remaining_students)}")
        print(f"  Remaining schools: {sorted(remaining_schools)}")
        print(f"  Top students: {sorted(top_students)}")

        # Case 1: Serial dictatorship (1 top-priority student)
        if len(top_students) == 1:
            student_name = list(top_students)[0]
            student = next(s for s in self.students if s.name == student_name)

            print(f"  → Serial dictatorship: asking {student_name} to pick")

            # Ask student to pick top school
            choice, reason = self._ask_pick_top(student, remaining_schools)

            node_info['type'] = 'serial_dictatorship'
            node_info['student'] = student_name
            node_info['choice'] = choice
            node_info['available'] = sorted(remaining_schools)
            node_info['reasoning'] = reason
            self.osp_tree_trace.append(node_info)

            # Assign and recurse
            matches[student_name] = choice
            student.osp_choices.append(choice)

            print(f"  → {student_name} chose {choice}")

            self._run_osp_tree(
                remaining_students - {student_name},
                remaining_schools - {choice},
                matches,
                node_path + [f"SD:{student_name}→{choice}"]
            )
            return

        # Case 2: Two top-priority students (acyclic case)
        if len(top_students) == 2:
            a_name, b_name = sorted(top_students)  # Alphabetical for consistency
            student_a = next(s for s in self.students if s.name == a_name)
            student_b = next(s for s in self.students if s.name == b_name)

            print(f"  → Two top students: {a_name} and {b_name}")

            # Phase a: Ask a about her priority-1 schools (NO keeps candidate available)
            a_priority1_schools = self._get_priority_one_schools(
                student_a, remaining_schools, remaining_students
            )

            print(f"  → Phase A: {a_name}'s priority-1 schools: {a_priority1_schools}")

            for candidate in a_priority1_schools:  # Already sorted alphabetically
                # In AG construction, saying NO does not remove candidate; fallback is full remaining set
                fallback = remaining_schools.copy()
                answer, reason = self._ask_yes_no(
                    student_a, candidate, fallback, remaining_schools
                )

                node_info_yes_no = node_info.copy()
                node_info_yes_no['type'] = 'yes_no_a'
                node_info_yes_no['student'] = a_name
                node_info_yes_no['candidate'] = candidate
                node_info_yes_no['fallback'] = sorted(fallback)
                node_info_yes_no['answer'] = 'YES' if answer else 'NO'
                node_info_yes_no['reasoning'] = reason
                self.osp_tree_trace.append(node_info_yes_no)

                print(f"  → Asked {a_name} about {candidate}: {'YES' if answer else 'NO'}")

                if answer:  # YES
                    matches[a_name] = candidate
                    student_a.osp_choices.append(candidate)
                    self._run_osp_tree(
                        remaining_students - {a_name},
                        remaining_schools - {candidate},
                        matches,
                        node_path + [f"A:{a_name}:YES→{candidate}"]
                    )
                    return
                # If NO: continue to next candidate

            # Phase b: Ask b about his priority-1 schools (NO keeps candidate available)
            b_priority1_schools = self._get_priority_one_schools(
                student_b, remaining_schools, remaining_students
            )

            print(f"  → Phase B: {b_name}'s priority-1 schools: {b_priority1_schools}")

            for candidate in b_priority1_schools:
                fallback = remaining_schools.copy()
                answer, reason = self._ask_yes_no(
                    student_b, candidate, fallback, remaining_schools
                )

                node_info_yes_no = node_info.copy()
                node_info_yes_no['type'] = 'yes_no_b'
                node_info_yes_no['student'] = b_name
                node_info_yes_no['candidate'] = candidate
                node_info_yes_no['fallback'] = sorted(fallback)
                node_info_yes_no['answer'] = 'YES' if answer else 'NO'
                node_info_yes_no['reasoning'] = reason
                self.osp_tree_trace.append(node_info_yes_no)

                print(f"  → Asked {b_name} about {candidate}: {'YES' if answer else 'NO'}")

                if answer:  # YES
                    matches[b_name] = candidate
                    student_b.osp_choices.append(candidate)
                    self._run_osp_tree(
                        remaining_students - {b_name},
                        remaining_schools - {candidate},
                        matches,
                        node_path + [f"B:{b_name}:YES→{candidate}"]
                    )
                    return

            # Phase c: Neither took anything, ask a then b for top pick
            print(f"  → Phase C: Both declined, asking for top picks")

            choice_a, reason_a = self._ask_pick_top(student_a, remaining_schools)
            node_info_pick_a = node_info.copy()
            node_info_pick_a['type'] = 'final_pick_a'
            node_info_pick_a['student'] = a_name
            node_info_pick_a['choice'] = choice_a
            node_info_pick_a['available'] = sorted(remaining_schools)
            node_info_pick_a['reasoning'] = reason_a
            self.osp_tree_trace.append(node_info_pick_a)

            matches[a_name] = choice_a
            student_a.osp_choices.append(choice_a)

            print(f"  → {a_name} picked {choice_a}")

            remaining_for_b = remaining_schools - {choice_a}
            choice_b, reason_b = self._ask_pick_top(student_b, remaining_for_b)
            node_info_pick_b = node_info.copy()
            node_info_pick_b['type'] = 'final_pick_b'
            node_info_pick_b['student'] = b_name
            node_info_pick_b['choice'] = choice_b
            node_info_pick_b['available'] = sorted(remaining_for_b)
            node_info_pick_b['reasoning'] = reason_b
            self.osp_tree_trace.append(node_info_pick_b)

            matches[b_name] = choice_b
            student_b.osp_choices.append(choice_b)

            print(f"  → {b_name} picked {choice_b}")

            self._run_osp_tree(
                remaining_students - {a_name, b_name},
                remaining_schools - {choice_a, choice_b},
                matches,
                node_path + [f"PICK:{a_name}→{choice_a},{b_name}→{choice_b}"]
            )
            return

        # Should not reach here with acyclic priorities
        raise RuntimeError(f"Invalid priority structure: {len(top_students)} top students. "
                         f"Expected 1 or 2 for acyclic priorities.")

    def _parse_reason_decision(self, text):
        """
        Parse <REASON> and <DECISION> tags from LLM response.

        Args:
            text: LLM response text

        Returns:
            Tuple[str, str]: (reason, decision_text)

        Raises:
            ValueError: If tags not found
        """
        # Parse REASON
        reason_pattern = r"<REASON>(.*?)</REASON>"
        reason_match = re.search(reason_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not reason_match:
            raise ValueError("REASON tag not found")
        reason = reason_match.group(1).strip()

        # Parse DECISION
        decision_pattern = r"<DECISION>(.*?)</DECISION>"
        decision_match = re.search(decision_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not decision_match:
            raise ValueError("DECISION tag not found")
        decision = decision_match.group(1).strip()

        return reason, decision

    def _extract_osp_choice_with_model(self, decision_text, student, available):
        """
        Use gpt-4o-mini to extract school choice from decision text.

        Args:
            decision_text: Text from <DECISION> tag
            student: Student object
            available: Set of available schools

        Returns:
            str: Extracted school choice
        """
        extract_model = (Model("openai/gpt-4o-mini", temperature=0, service_name="open_router")
                         if os.environ.get("OPEN_ROUTER_API_KEY") and not os.environ.get("OPENAI_API_KEY")
                         else Model("gpt-4o-mini", temperature=0))  # route extraction via OpenRouter when only that key exists (2026-07-08)

        available_str = ", ".join(sorted(available))
        extraction_prompt = f"""Extract the school choice from this text. The student must choose ONE school from: {available_str}

Text: {decision_text}

Respond with ONLY the school letter (w, x, y, or z). Nothing else."""

        q_extract = QuestionFreeText(
            question_name="extract_osp_choice",
            question_text=extraction_prompt
        )

        result = Survey([q_extract]).by(extract_model).run()
        extracted = result.select("extract_osp_choice").to_list()[0].lower().strip()

        # Parse extracted choice
        for school in ['w', 'x', 'y', 'z']:
            if school in extracted:
                if school in available:
                    return school

        raise ValueError(f"Could not extract valid choice from: {extracted}")

    def _record_outcomes(self, matches):
        """Store outcomes in student objects."""
        for student in self.students:
            student.matched_school = matches[student.name]
            student.utility = student.get_utility(student.matched_school)
            print(f"{student.name}: matched to {student.matched_school}, utility={student.utility}")

    def _compute_osp_truthfulness(self):
        """
        Compute truthfulness for true OSP mechanism.

        For yes/no nodes: YES is truthful iff candidate is top among remaining_set
        For pick nodes: choice is truthful iff it's top among available

        Returns:
            Dict[student_name, bool]: Truthfulness for each student
        """
        truthfulness = {}

        for student in self.students:
            is_truthful = True

            # Check each node in tree trace where this student was queried
            for node in self.osp_tree_trace:
                if node.get('student') != student.name:
                    continue

                node_type = node['type']

                if node_type in ['yes_no_a', 'yes_no_b']:
                    # Yes/no question
                    candidate = node['candidate']
                    # Reconstruct remaining set: fallback + {candidate}
                    fallback = set(node.get('fallback', []))
                    remaining_set = fallback | {candidate}
                    answer = (node['answer'] == 'YES')

                    # Determine if candidate is top choice among remaining
                    remaining_values = {
                        school: student.values[school]
                        for school in remaining_set
                        if school in student.values
                    }

                    if remaining_values:
                        best_school = max(remaining_values.items(), key=lambda x: x[1])[0]
                        truthful_answer = (candidate == best_school)

                        if answer != truthful_answer:
                            is_truthful = False
                            print(f"{student.name} MISREPORTED at yes/no node:")
                            print(f"  Candidate: {candidate}")
                            print(f"  Remaining: {sorted(remaining_set)}")
                            print(f"  Values: {remaining_values}")
                            print(f"  Best: {best_school} (${student.values[best_school]})")
                            print(f"  Answer: {'YES' if answer else 'NO'}")
                            print(f"  Truthful: {'YES' if truthful_answer else 'NO'}")
                            break

                elif node_type in ['serial_dictatorship', 'final_pick_a', 'final_pick_b']:
                    # Pick question
                    choice = node['choice']
                    # Get available schools from node context (prefer explicit 'available')
                    available = set(node.get('available', node.get('remaining_schools', [])))

                    if available:
                        available_values = {
                            school: student.values[school]
                            for school in available
                            if school in student.values
                        }

                        if available_values:
                            best_school = max(available_values.items(), key=lambda x: x[1])[0]

                            if choice != best_school:
                                is_truthful = False
                                print(f"{student.name} MISREPORTED at pick node:")
                                print(f"  Available: {sorted(available)}")
                                print(f"  Values: {available_values}")
                                print(f"  Best: {best_school} (${student.values[best_school]})")
                                print(f"  Chose: {choice} (${student.values[choice]})")
                                break

            truthfulness[student.name] = is_truthful

        # Calculate overall truthfulness rate
        truthful_count = sum(truthfulness.values())
        total_count = len(truthfulness)
        truthfulness_rate = truthful_count / total_count if total_count > 0 else 0

        print(f"\nTrue OSP Truthfulness rate: {truthfulness_rate:.1%}")

        return truthfulness


class DA_plan:
    """
    Orchestrates DA experiments.
    Parallel to Auction_plan class.
    """
    def __init__(self, number_students, number_schools, rule, output_dir,
                 timestring=None, cache=None, model='gpt-4o', temperature=0,
                 service_name=None, config_dict=None, experiment_index=None):
        """
        Initialize DA plan.

        Args:
            number_students: Number of students (fixed at 4)
            number_schools: Number of schools (fixed at 4)
            rule: Rule_DA instance
            output_dir: Output directory for results (base folder, not run_*)
            timestring: Timestamp string for filenames
            cache: EDSL Cache instance
            model: Model name
            temperature: LLM temperature
            service_name: Optional service name for Model
            config_dict: Optional config dictionary to save
            experiment_index: Index of this experiment (for numbering)
        """
        import pandas as pd

        self.rule = rule
        self.students = []
        self.number_students = number_students
        self.number_schools = number_schools

        # Initialize model
        if service_name:
            self.model = Model(model, temperature=temperature, service_name=service_name)
        else:
            self.model = Model(model, temperature=temperature)

        self.cache = cache
        self.output_dir = output_dir  # No run_{timestamp} subfolder
        self.experiment_index = experiment_index

        # Generate timestring if not provided
        if timestring is None:
            timestring = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        self.timestring = timestring

        # Create subdirectories (only once)
        self.raw_data_dir = os.path.join(self.output_dir, "raw_data")
        self.results_dir = os.path.join(self.output_dir, "results")
        self.prompts_dir = os.path.join(self.output_dir, "prompts")

        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.prompts_dir, exist_ok=True)

        # Save config if provided (only once, check if already exists)
        self.config_dict = config_dict
        config_path = os.path.join(self.output_dir, "config.yaml")
        if config_dict and not os.path.exists(config_path):
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            print(f"Config saved to: {config_path}")

        # Data storage
        self.values_list = {}  # {school: [values per student]}
        self.priorities_structure = None  # Fixed acyclic priorities
        self.data_to_save = {}

    def draw_values(self, seed=1234):
        """
        Generate values using common + private structure.
        Similar to affiliated value auctions.

        Args:
            seed: Random seed for reproducibility
        """
        random.seed(seed)
        print(f"\nGenerating values with seed={seed}...")

        self.values_list = {school: [] for school in ["w", "x", "y", "z"]}

        for school in ["w", "x", "y", "z"]:
            # Draw common value for this school
            common_value = random.randint(self.rule.common_range[0],
                                          self.rule.common_range[1])

            # Each student gets common + private shock
            for student_idx in range(self.number_students):
                private_shock = random.randint(0, self.rule.private_range)
                total_value = common_value + private_shock
                self.values_list[school].append(total_value)

            print(f"  School {school}: common={common_value}, values={self.values_list[school]}")

        # Generate fixed acyclic priorities
        self.priorities_structure = self._generate_acyclic_priorities()
        print(f"\nFixed acyclic priorities:")
        for school, prios in self.priorities_structure.items():
            print(f"  {school}: {prios}")

        # Generate global ranking (social information)
        self.global_ranking = self._compute_global_ranking(
            strategy=self.rule.global_ranking_strategy
        )
        print(f"\nGlobal ranking ({self.rule.global_ranking_strategy}): {self.global_ranking}")

    def _generate_acyclic_priorities(self):
        """
        Return fixed Ergin-acyclic priority structure.
        From readme: Top-2 = {A, B}, Bottom-2 = {C, D}

        Returns:
            Dict[school, Dict[student_name, priority_rank]]
        """
        return {
            "w": {"Student A": 1, "Student B": 2, "Student C": 3, "Student D": 4},
            "x": {"Student B": 1, "Student A": 2, "Student C": 3, "Student D": 4},
            "y": {"Student A": 1, "Student B": 2, "Student D": 3, "Student C": 4},
            "z": {"Student B": 1, "Student A": 2, "Student D": 3, "Student C": 4}
        }

    def _compute_global_ranking(self, strategy="average"):
        """
        Compute global ranking of schools to provide social information.

        Args:
            strategy: How to compute ranking
                - "average": Based on average values across students
                - "truthful": Based on actual student preferences (if known)
                - "fixed": Fixed ranking for all experiments
                - "random": Random ranking
                - "misleading": Reverse of average (for experiments)

        Returns:
            str: Ranking string like "y > x > w > z"
        """
        if strategy == "average":
            # Compute average value for each school
            avg_values = {}
            for school in ["w", "x", "y", "z"]:
                avg_values[school] = sum(self.values_list[school]) / len(self.values_list[school])

            # Sort by average value (descending)
            sorted_schools = sorted(avg_values.items(), key=lambda x: x[1], reverse=True)
            ranking = " > ".join([school for school, _ in sorted_schools])

            print(f"  Average values: {avg_values}")
            return ranking

        elif strategy == "fixed":
            # Fixed ranking (can be used as control condition)
            return "y > x > w > z"

        elif strategy == "random":
            # Random ranking
            schools = ["w", "x", "y", "z"]
            random.shuffle(schools)
            return " > ".join(schools)

        elif strategy == "misleading":
            # Reverse of average (for testing effects of misinformation)
            avg_values = {}
            for school in ["w", "x", "y", "z"]:
                avg_values[school] = sum(self.values_list[school]) / len(self.values_list[school])

            sorted_schools = sorted(avg_values.items(), key=lambda x: x[1], reverse=False)  # Ascending!
            ranking = " > ".join([school for school, _ in sorted_schools])

            print(f"  ⚠️  Misleading ranking (reversed)")
            return ranking

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def build_students(self):
        """Create Student instances with values and priorities."""
        student_names = ["A", "B", "C", "D"]

        print(f"\nBuilding {self.number_students} students...")

        for i in range(self.number_students):
            # Extract values for this student
            value_dict = {}
            for school in ["w", "x", "y", "z"]:
                value_dict[school] = self.values_list[school][i]

            # Extract priorities for this student
            priority_dict = {}
            student_name = f"Student {student_names[i]}"
            for school in ["w", "x", "y", "z"]:
                priority_dict[school] = self.priorities_structure[school][student_name]

            student = Student(
                value_dict=value_dict,
                priority_dict=priority_dict,
                name=student_names[i],
                rule=self.rule
            )
            self.students.append(student)

            print(f"  {student.name}: values={value_dict}, priorities={priority_dict}")

    def run(self):
        """
        Execute one DA round.
        Dispatch to DA_Direct or DA_OSP based on mechanism type.

        Returns:
            Dict with results
        """
        print(f"\n{'='*70}")
        print(f"Running DA Mechanism: {self.rule.mechanism_type}")
        print(f"{'='*70}")

        if self.rule.mechanism_type == "direct":
            da_mechanism = DA_Direct(
                students=self.students,
                rule=self.rule,
                model=self.model,
                cache=self.cache,
                global_ranking=self.global_ranking  # Pass global ranking
            )
            results = da_mechanism.run()

        elif self.rule.mechanism_type == "osp":
            da_mechanism = DA_OSP(
                students=self.students,
                rule=self.rule,
                model=self.model,
                cache=self.cache,
                global_ranking=self.global_ranking  # Pass global ranking
            )
            results = da_mechanism.run()

        else:
            raise ValueError(f"Unknown mechanism: {self.rule.mechanism_type}")

        # Store results
        self._record_results(results)

        return results

    def _record_results(self, results):
        """Store results in data structure."""
        matches = results['matches']

        # Build data structure
        self.data_to_save = {
            "mechanism_type": self.rule.mechanism_type,
            "global_ranking": self.global_ranking,  # Add global ranking info
            "global_ranking_strategy": self.rule.global_ranking_strategy,  # Add strategy info
            "values": {s.name: s.values for s in self.students},
            "priorities": {s.name: s.priorities for s in self.students},
            "matches": matches,
            "utilities": {s.name: s.utility for s in self.students}
        }

        # Add mechanism-specific data
        if self.rule.mechanism_type == "direct":
            self.data_to_save["rankings"] = {s.name: s.submitted_ranking for s in self.students}
            self.data_to_save["reasoning"] = results.get('reasoning', {})  # Add reasoning
            self.data_to_save["truthfulness"] = results.get('truthfulness', {})  # Add truthfulness
            self.data_to_save["da_trace"] = results.get('da_trace', [])

            # Compute overall truthfulness rate
            truthfulness_list = list(results.get('truthfulness', {}).values())
            if truthfulness_list:
                truthfulness_rate = sum(truthfulness_list) / len(truthfulness_list)
                self.data_to_save["truthfulness_rate"] = truthfulness_rate
                print(f"\n  Truthfulness rate: {truthfulness_rate:.1%}")

        elif self.rule.mechanism_type == "osp":
            self.data_to_save["osp_choices"] = {s.name: s.osp_choices for s in self.students}
            # Support both old 'osp_history' and new 'osp_tree_trace' formats
            if 'osp_tree_trace' in results:
                self.data_to_save["osp_history"] = results['osp_tree_trace']  # Store as osp_history for consistency
            else:
                self.data_to_save["osp_history"] = results.get('osp_history', [])
            self.data_to_save["truthfulness"] = results.get('truthfulness', {})

            # Use truthfulness_rate from results if available
            if 'truthfulness_rate' in results:
                self.data_to_save["truthfulness_rate"] = results['truthfulness_rate']
                print(f"\n  Overall OSP Truthfulness rate: {results['truthfulness_rate']:.1%}")
            else:
                # Compute overall truthfulness rate (fallback)
                truthfulness_list = list(results.get('truthfulness', {}).values())
                if truthfulness_list:
                    truthfulness_rate = sum(truthfulness_list) / len(truthfulness_list)
                    self.data_to_save["truthfulness_rate"] = truthfulness_rate
                    print(f"\n  Overall OSP Truthfulness rate: {truthfulness_rate:.1%}")

        print(f"\n{'='*70}")
        print("FINAL RESULTS")
        print(f"{'='*70}")
        print(f"Matches: {matches}")
        print(f"Utilities: {self.data_to_save['utilities']}")

    def copy_prompts(self):
        """Copy all prompt files to the prompts directory (only once)."""
        import shutil

        # Copy main template file (check if already exists)
        template_name = self.rule.special_name or f"da_{self.rule.mechanism_type}_traditional.txt"
        template_src = os.path.join(self.rule.templates_dir, template_name)
        template_dst = os.path.join(self.prompts_dir, template_name)
        if os.path.exists(template_src) and not os.path.exists(template_dst):
            shutil.copy2(template_src, template_dst)

        # Copy da_ask.txt (check if already exists)
        da_ask_src = os.path.join(prompt_dir, 'da_ask.txt')
        da_ask_dst = os.path.join(self.prompts_dir, 'da_ask.txt')
        if os.path.exists(da_ask_src) and not os.path.exists(da_ask_dst):
            shutil.copy2(da_ask_src, da_ask_dst)
            print(f"Prompts copied to: {self.prompts_dir}")

    def data_to_json(self):
        """Export results to JSON file in raw_data subdirectory."""
        # Copy prompts (will only copy once)
        self.copy_prompts()

        # Use experiment_index for filename if available, otherwise use timestring
        if self.experiment_index is not None:
            filename = f"result_{self.experiment_index}_{self.timestring}.json"
        else:
            filename = f"result_{self.timestring}.json"

        # Save to raw_data subdirectory (like auction experiments)
        filepath = save_json(self.data_to_save, filename, self.raw_data_dir)
        print(f"\nResults saved to: {filepath}")

        return filepath
