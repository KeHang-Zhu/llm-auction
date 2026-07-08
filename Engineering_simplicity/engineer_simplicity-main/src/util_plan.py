import textwrap
from textwrap import dedent
from itertools import cycle
import random
import json
import os
import sys
from edsl import Model
from edsl import Agent, Scenario, Survey
from edsl import Cache
from edsl.base import Base
from edsl.questions import QuestionFreeText, QuestionYesNo
from edsl.prompts import Prompt
from edsl.questions import QuestionNumerical
from jinja2 import Template
import re
import yaml
from functools import lru_cache

current_script_path = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_script_path, '../rule_template/V10/')
prompt_dir = os.path.join(current_script_path, '../Prompt/')

# c = Cache()  

@lru_cache(maxsize=1)
def load_payment_examples(path: str):
    """
    Load payment example text snippets from a YAML file.
    Returns an empty dict if the file is missing or invalid.
    """
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        return {}
    except Exception as exc:
        print(f"Warning: failed to load payment examples from {path}: {exc}")
    return {}

def save_json(data, filename, directory):
    """Save data to a JSON file in the specified directory."""
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    return file_path

class Rule_plan:
    '''
    This class defines different auction rules and their behaviors.
    '''
    def __init__(self, seal_clock,  private_value, open_blind, rounds,
                 ascend_descend="ascend",
                 price_order = "second",
                 common_range=[10, 80], private_range=20, increment=1, number_agents=3, special_name="", start_price=0, turns=20, closing= False, reserve_price = 0,
                 include_payment_example=False, payment_example_key=None, payment_examples_path=None,
                 templates_dir=None, use_survey=False, survey_price_points=15):
        self.seal_clock = seal_clock
        self.ascend_descend = ascend_descend
        self.private_value = private_value
        self.open_blind = open_blind
        self.price_order = price_order
        self.round = rounds
        self.turns = turns
        self.common_range = common_range
        self.private_range = private_range
        self.increment = increment
        self.number_agents = number_agents
        self.start_price= start_price
        self.closing = closing
        self.reserve_price = reserve_price
        self.use_survey = use_survey
        self.survey_price_points = survey_price_points

        # Use provided templates_dir or fall back to global default
        if templates_dir is None:
            # Use global templates_dir defined at module level
            _templates_dir = globals()['templates_dir']
        else:
            # Use provided templates_dir (resolve relative paths)
            if not os.path.isabs(templates_dir):
                _templates_dir = os.path.join(current_script_path, '..', templates_dir)
            else:
                _templates_dir = templates_dir

        ## Rule prompt
        # intro_string = Prompt.from_txt(os.path.join(_templates_dir,"intro.txt"))
        # intro = intro_string.render({"n":self.round})

        # value_explain_string = Prompt.from_txt(os.path.join(_templates_dir,f"intro_{self.private_value}.txt"))
        # value_explain = value_explain_string.render({"increment":self.increment,"common_low":self.common_range[0], "common_high":self.common_range[1],"private":self.private_range, "num_bidders": self.number_agents-1})
        if special_name:
            game_type_string = Prompt.from_txt(os.path.join(_templates_dir,special_name))
            game_type = game_type_string.render({
                "item_description": "256GB IPhone 16 pro",
                "item_condition": "used",
                "start_price":  0,
                "num_rounds": self.turns, 
                "bid_increment":self.increment,
                "private":self.private_range,
                "increment":self.increment,
                "num_bidders": self.number_agents-1,
                "n":self.round,
                "common_low":self.common_range[0], 
                "common_high":self.common_range[1],
            })
        else:
            if self.seal_clock == 'clock':
                game_type_string = Prompt.from_txt(os.path.join(_templates_dir,f"{self.ascend_descend}_{self.private_value}_{self.open_blind}.txt"))
            elif self.seal_clock == 'seal':
                game_type_string = Prompt.from_txt(os.path.join(_templates_dir,f"{self.price_order}_price_{self.private_value}.txt"))
            game_type = game_type_string.render({"increment":self.increment,"min_price":self.common_range[0],"max_price":self.common_range[1]+self.private_range, "common_low":self.common_range[0], "common_high":self.common_range[1],"num_bidders": self.number_agents-1, "private":self.private_range, "n":self.round})
        
        # if self.round > 1:
        #     multi_string = Prompt.from_txt(os.path.join(templates_dir,"multi.txt"))
        #     ending = multi_string.render({"n":self.round})
        # else:
        #     ending = ''
        
        ## Combine the rule prompt
        self.rule_explanation =  game_type

        if include_payment_example:
            examples_path = payment_examples_path or os.path.join(prompt_dir, "payment_examples.yaml")
            examples = load_payment_examples(examples_path)
            key = (payment_example_key or self._default_payment_example_key()).lower()
            example_text = examples.get(key)
            if example_text:
                self.rule_explanation = f"{self.rule_explanation}\n\nPayment example: {example_text}"
        
        persona_str = Prompt.from_txt(os.path.join(prompt_dir,"persona.txt"))
        self.persona = str(persona_str.render({}))

        ## Bid asking prompt
        if self.seal_clock == "seal":
            ask_str = Prompt.from_txt(os.path.join(prompt_dir,"asking_sealed.txt"))
            self.asking_prompt = str(ask_str.render({}))
        elif self.seal_clock == "clock":
            if self.ascend_descend == "ascend":
                self.asking_prompt = "Do you want to stay in the bidding?"
            elif self.asking_prompt == "descend":
                self.asking_prompt = "Do you want to accept the current price?"

    def _default_payment_example_key(self):
        if self.seal_clock == "clock":
            return "clock_open" if self.open_blind == "open" else "clock_closed"
        return self.price_order
                
    def describe(self):
        # Provides a description of the auction rule
        print(f"Auction Type: {self.seal_clock}, \nBidding Order: {self.ascend_descend}, \nValue Type: {self.private_value}, \n Information Type: {self.open_blind}, \n price order: {self.price_order}")


class SealBid():
    def __init__(self, agents, rule, model, cache= None, history=None):
        
        ## for setting up stage
        self.rule = rule
        self.agents = agents
        ## For repeated game:
        self.history = history
        self.model = model
        self.cache = cache
        
        # self.scenario = Scenario({
        #     'agent_1_name': agents[0].name, 
        #     'agent_2_name': agents[1].name, 
        #     'the history of this game': self.history
        #     }) 
        
        ## for bidding 
        self.bid_list = []
        self.winner = None
        
        
    def __repr__(self):
        return f'Sealed Bid Auction: (bid_list={self.bid_list})'

    def build_history_section(self, agent):
        """
        Build history information string containing all rounds' bids, results, and plans.

        Args:
            agent: Bidder object

        Returns:
            Formatted history string, empty for first round
        """
        if not agent.history or len(agent.history) == 0:
            return ""

        history_lines = ["=" * 70]
        history_lines.append("HISTORY OF PREVIOUS ROUNDS")
        history_lines.append("=" * 70)

        for i, hist in enumerate(agent.history):
            history_lines.append(f"\n{'─' * 70}")
            history_lines.append(f"ROUND {i + 1}")
            history_lines.append(f"{'─' * 70}")
            history_lines.append(f"Your plan: {agent.reasoning[i] if i < len(agent.reasoning) else 'N/A'}")
            history_lines.append(f"\nResults: {hist}")

        history_lines.append(f"\n{'=' * 70}")
        history_lines.append("CURRENT ROUND")
        history_lines.append(f"{'=' * 70}\n")

        return "\n".join(history_lines)

    def parse_plan_and_action(self, text):
        """
        Parse LLM response for <PLAN> and <ACTION> tags with robust handling.

        Args:
            text: LLM response text

        Returns:
            (plan, action) tuple

        Raises:
            ValueError: If parsing fails
        """
        # Parse PLAN
        plan_pattern = r"<PLAN>(.*?)</PLAN>"
        plan_match = re.search(plan_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not plan_match:
            raise ValueError("PLAN tag not found")
        plan = plan_match.group(1).strip()

        # Parse ACTION with robust handling
        # First, try to extract content between ACTION tags (including brackets, spaces, etc.)
        action_content_pattern = r"<ACTION>(.*?)</ACTION>"
        action_content_match = re.search(action_content_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not action_content_match:
            raise ValueError("ACTION tag not found")

        action_content = action_content_match.group(1).strip()

        # Now extract the number from the content (handles formats like "[45]", "45", " 45 ", etc.)
        number_pattern = r"(\d+(?:\.\d+)?)"
        number_match = re.search(number_pattern, action_content)
        if not number_match:
            raise ValueError("ACTION tag must contain a valid number")

        action = number_match.group(1).strip()

        return plan, action


    def run(self):
        '''run for one round using parallel Survey (Mechanism 1: within-round parallelization)'''

        # STEP 1: Build prompts for all agents upfront
        agent_prompts = []
        agent_metadata = []

        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            instruction_str = Prompt.from_txt(os.path.join(prompt_dir,"instruction.txt"))
            instruction = str(instruction_str.render({"name":agent.name, "other_agent_names": other_agent_names}))

            general_prompt = instruction + self.rule.persona +"\n" + str(self.rule.rule_explanation) + "\n"

            # Build history section
            history_section = self.build_history_section(agent)

            # Build transcript (empty for sealed bid, but included for consistency)
            transcript = ""

            # Determine round number
            current_round = len(agent.reasoning) + 1
            total_rounds = self.rule.round

            # Use unified template
            unified_template = Prompt.from_txt(os.path.join(prompt_dir, "unified_sealed_bid.txt"))
            prompt_content = str(unified_template.render({
                "history_section": history_section,
                "current_round": current_round,
                "total_rounds": total_rounds,
                "current_value": agent.current_value,
                "transcript": transcript
            }))

            full_prompt = general_prompt + prompt_content
            agent_prompts.append(full_prompt)
            agent_metadata.append({
                'agent': agent,
                'current_round': current_round
            })

        # STEP 2: Create parallel Survey with unique question names
        questions = []
        for i, full_prompt in enumerate(agent_prompts):
            agent = agent_metadata[i]['agent']
            agent_name = agent.name.replace(" ", "_")

            q_bid = QuestionFreeText(
                question_name=f"q_bid_{agent_name}",
                question_text=full_prompt
            )
            questions.append(q_bid)

        # STEP 3: Execute all LLM calls in parallel
        survey = Survey(questions=questions)
        result = survey.by(self.model).run(cache=self.cache)

        # STEP 4: Parse all responses and handle retries
        for i, metadata in enumerate(agent_metadata):
            agent = metadata['agent']
            agent_name = agent.name.replace(" ", "_")
            question_name = f"q_bid_{agent_name}"

            response = result.select(question_name).to_list()[0]

            # Call helper method to handle parsing and retries
            bid, plan = self._parse_and_validate_bid(
                response, agent, metadata['current_round'], agent_prompts[i]
            )

            # Store plan and bid
            agent.reasoning.append(plan)
            self.bid_list.append({"agent":agent.name,"bid": bid})
            agent.submitted_bids.append(bid)

        print(self.bid_list, '\n Value list:',[agent.current_value for agent in self.agents])
        self.declare_winner_and_price()
        print(self.winner)
        return {'bidding history':self.bid_list, 'winner':self.winner}


    def _parse_and_validate_bid(self, initial_response, agent, current_round, full_prompt):
        '''
        Handle parsing, validation, and retry logic for a single agent's bid.

        Args:
            initial_response: Initial LLM response from parallel Survey
            agent: Bidder object
            current_round: Current round number
            full_prompt: Agent's full prompt (for retry)

        Returns:
            (bid, plan) tuple

        Raises:
            RuntimeError: If all retry attempts fail
        '''
        retry_attempts = 3
        attempt = 0
        format_warning = ''
        response = initial_response

        while attempt < retry_attempts:
            try:
                # Print response with clear separator
                print("\n" + "="*70)
                print(f"[SealBid] LLM Response (Agent: {agent.name}, Round: {current_round}, Attempt: {attempt+1})")
                print("="*70)
                print(response)
                print("="*70 + "\n")

                # Parse PLAN and ACTION
                plan, action = self.parse_plan_and_action(response)
                bid = float(action)

                # Validate PLAN content
                if len(plan) == 0:
                    raise ValueError("PLAN cannot be empty")

                # Validate bid range (only check lower bound)
                if bid < 0:
                    raise ValueError(f"Bid {bid} must be non-negative")

                # Validate bid increment (handle floating point precision)
                remainder = abs(bid % self.rule.increment)
                if remainder > 1e-9 and abs(remainder - self.rule.increment) > 1e-9:
                    raise ValueError(f"Bid {bid} must be a multiple of increment {self.rule.increment}")

                return bid, plan  # Success

            except (ValueError, TypeError) as e:
                print(f"Error processing bid: {e}. Retrying ({attempt + 1}/{retry_attempts})...")
                attempt += 1

                if attempt < retry_attempts:
                    # Retry individually for this agent only (doesn't affect other successful agents)
                    format_warning = f"\n\nWrong format or invalid value. Error: {str(e)}. You MUST follow the output format!"
                    q_retry = QuestionFreeText(
                        question_name="q_bid_retry",
                        question_text=full_prompt + format_warning
                    )
                    survey_retry = Survey(questions=[q_retry])
                    result_retry = survey_retry.by(self.model).run(cache=self.cache)
                    response = result_retry.select("q_bid_retry").to_list()[0]

        raise RuntimeError(f"Failed to process bid for {agent.name} after {retry_attempts} attempts")



    def declare_winner_and_price(self):
        '''Sort the bid list by the 'bid' key in descending order to find the highest bids'''
        sorted_bids = sorted(self.bid_list, key=lambda x: float(x['bid']), reverse=True)

        if self.rule.price_order == "first":
            if len(sorted_bids) > 0:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[0]["bid"]
        elif self.rule.price_order == "second":
            if len(sorted_bids) > 1:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[1]["bid"]
        elif self.rule.price_order == "third":
            if len(sorted_bids) > 2:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[2]["bid"]
        elif self.rule.price_order == "allpay":
            if len(sorted_bids) > 0:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[0]["bid"]
        else: 
            raise ValueError(f"Rule {self.rule.price_order} not allowed")
        
        self.winner = {'winner':winner, 'price':price}
        for agent in self.agents:
            ## implement the all pay auction
            if self.rule.price_order == "allpay":
                for bid in self.bid_list:
                    if bid["agent"] == agent.name:
                        price = bid["bid"]
                if agent.name == winner:
                    agent.winning.append(True)
                    agent.profit.append(agent.current_value - price)
                else:
                    agent.winning.append(False)
                    agent.profit.append(- price)
            else:
                if agent.name == winner:
                    if self.rule.private_value == "private" or self.rule.private_value == "affiliated":
                        agent.profit.append(agent.current_value - float(price))
                    elif self.rule.private_value == "common":
                        agent.profit.append(agent.current_common - float(price))
                    agent.winning.append(True)
                else:
                    agent.profit.append(0)
                    agent.winning.append(False)
    
class Clock():
    def __init__(self, agents, rule, model, cache=None, history=None, extraction_model=None):

        ## for setting up stage
        self.rule = rule
        self.agents = agents[:]
        self.change = self.rule.increment
        self.current_price = rule.common_range[0]
        self.model = model
        self.cache = cache

        # Add extraction model for yes/no distillation
        if extraction_model is None:
            # Use the same model and service_name as the main model for consistency
            extraction_model = self.model
        self.extraction_model = extraction_model
        ## For repeated game:
        self.history = history
        
        if self.rule.ascend_descend == "ascend":
            self.agent_left = agents[:]
        elif self.rule.ascend_descend == "descend":
            self.agent_left = []
        
        # For bidding storage
        self.clock = 0
        self.exit_number = 0
        self.current_bid = []
        self.bid_list = []    
        self.transcript = []
        self.exit_list = []
        self.winner = None
    
    def __repr__(self):
        return f'Clock Auction: (bid_list={self.bid_list})'

    def parse_plan_and_action_clock(self, text):
        """
        [DEPRECATED] Parse Clock auction response for <PLAN> and <ACTION> tags.

        This function is kept for reference but ACTION parsing is now done via
        extract_yesno_with_model() using gpt-4o-mini. PLAN extraction still uses
        regex in _parse_and_validate_clock_action().

        Args:
            text: LLM response text

        Returns:
            (plan, action) tuple, action is "yes" or "no"

        Raises:
            ValueError: If parsing fails
        """
        # Parse PLAN
        plan_pattern = r"<PLAN>(.*?)</PLAN>"
        plan_match = re.search(plan_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not plan_match:
            raise ValueError("PLAN tag not found")
        plan = plan_match.group(1).strip()

        # Parse ACTION with robust handling
        # First, extract content between ACTION tags
        action_content_pattern = r"<ACTION>(.*?)</ACTION>"
        action_content_match = re.search(action_content_pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not action_content_match:
            raise ValueError("ACTION tag not found")

        action_content = action_content_match.group(1).strip()

        # Now extract yes/no from the content (handles formats like "[Yes]", "Yes", " No ", etc.)
        yes_no_pattern = r"\b(yes|no)\b"
        yes_no_match = re.search(yes_no_pattern, action_content, flags=re.IGNORECASE)
        if not yes_no_match:
            raise ValueError("ACTION tag must contain 'Yes' or 'No'")

        action = yes_no_match.group(1).lower()

        return plan, action

    def extract_yesno_with_model(self, full_response_text, extraction_model=None):
        """
        Use gpt-4o-mini to extract yes/no from a full text response.

        Args:
            full_response_text: The complete FreeText response from the agent
            extraction_model: Model instance to use (defaults to gpt-4o-mini)

        Returns:
            str: "yes" or "no" (lowercase)

        Raises:
            ValueError: If model fails to extract a valid yes/no
        """
        if extraction_model is None:
            # Use the main model for extraction if no extraction model provided
            extraction_model = self.model

        q_extract = QuestionYesNo(
            question_name="extract_yesno",
            question_text=f"""Given the following response from a bidder in a clock auction,
determine if they want to STAY IN the bidding (Yes) or EXIT the bidding (No).

The response may contain an <ACTION> tag with Yes/No, or express the decision
in natural language. Extract the bidder's decision.

Bidder Response:
{full_response_text}

Does the bidder want to STAY IN the bidding?"""
        )

        survey = Survey(questions=[q_extract])
        result = survey.by(extraction_model).run(cache=self.cache)
        response = result.select("extract_yesno").to_list()[0]

        if isinstance(response, str):
            return response.lower()
        else:
            raise ValueError(f"Invalid extraction result: {response}")

    def build_history_section_clock(self):
        """
        Build history information string for clock auctions.

        Returns:
            Formatted history string, empty for first period
        """
        if not self.transcript or len(self.transcript) == 0:
            return ""

        history_lines = ["=== History of Previous Periods ==="]
        for trans in self.transcript:
            history_lines.append(trans)
        history_lines.append("\n=== Current Period ===")

        return "\n".join(history_lines)

    def dynamic(self):
        if self.rule.ascend_descend == "ascend":
            self.current_price +=self.change
        elif self.rule.ascend_descend == "descend":
            self.current_price -=self.change
        else:
            raise ValueError(f"Rule {self.rule.ascend_descend} not allowed")
    
    def run_one_clock(self, counterfact=None):
        '''run for one period using parallel Survey (Mechanism 1: within-period parallelization)'''
        self.exit_number = 0
        print("===========",self.current_price)
        agent_in_play = self.agent_left[:]  # Keep snapshot mechanism

        # STEP 1: Build prompts for all active agents upfront
        agent_prompts = []
        agent_metadata = []

        for agent in agent_in_play:
            other_agent_names = ', '.join([a.name for a in agent_in_play if a is not agent])
            instruction_str = Prompt.from_txt(os.path.join(prompt_dir,"instruction.txt"))
            instruction = str(instruction_str.render(
                {"name":agent.name, "other_agent_names": other_agent_names})
                )

            general_prompt = instruction +"\n"+ str(self.rule.rule_explanation) +"\n"

            # Build history section
            history_section = self.build_history_section_clock()

            # Build transcript
            transcript = "\n".join(self.transcript) if self.transcript else ""

            # Use unified clock template
            unified_template = Prompt.from_txt(os.path.join(prompt_dir, "unified_clock.txt"))
            prompt_content = str(unified_template.render({
                "history_section": history_section,
                "clock_cycle": self.clock + 1,
                "current_value": agent.current_value,
                "current_price": self.current_price,
                "next_price": self.current_price + self.rule.increment,
                "transcript": transcript
            }))

            full_prompt = general_prompt + prompt_content
            agent_prompts.append(full_prompt)
            agent_metadata.append({'agent': agent})

        # STEP 2: Create parallel Survey with unique question names
        questions = []
        for i, full_prompt in enumerate(agent_prompts):
            agent = agent_metadata[i]['agent']
            agent_name = agent.name.replace(" ", "_")

            q_action = QuestionFreeText(
                question_name=f"q_action_{agent_name}_clock_{self.clock}",
                question_text=full_prompt
            )
            questions.append(q_action)

        # STEP 3: Execute all LLM calls in parallel
        survey = Survey(questions=questions)
        result = survey.by(self.model).run(cache=self.cache)

        # STEP 4: Parse all responses and process dropout decisions
        for i, metadata in enumerate(agent_metadata):
            agent = metadata['agent']
            agent_name = agent.name.replace(" ", "_")
            question_name = f"q_action_{agent_name}_clock_{self.clock}"

            response_text = result.select(question_name).to_list()[0]

            # Call helper method to handle parsing and retries
            plan, action = self._parse_and_validate_clock_action(
                response_text, agent, agent_prompts[i]
            )

            # Store the plan
            if len(agent.reasoning) <= self.clock:
                agent.reasoning.append(plan)
            else:
                agent.reasoning[self.clock] = plan

            print("=========", agent.name, action)

            # Process dropout decision (keep existing logic)
            if self.rule.ascend_descend == 'ascend':
                if action.lower() == 'no':
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": action.lower()})
                    self.agent_left.remove(agent)
                    agent.exit_price.append(str(self.current_price))
                    self.exit_number += 1
                    self.exit_list.append({"agent":agent.name,"bid": self.current_price})
                else:
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": action.lower()})
            elif self.rule.ascend_descend == 'descend':
                if action.lower() == 'yes':
                    self.agent_left.append(agent)
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": action.lower()})
                    agent.exit_price.append(str(self.current_price))
                else:
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": action.lower()})

        ## update the shared information
        self.transcript.append(self.share_information())

        print("One clock done")


    def _parse_and_validate_clock_action(self, initial_response, agent, full_prompt):
        '''
        Handle parsing, validation, and retry logic for a single agent's clock action.

        Args:
            initial_response: Initial LLM response from parallel Survey
            agent: Bidder object
            full_prompt: Agent's full prompt (for retry)

        Returns:
            (plan, action) tuple where action is "yes" or "no"

        Raises:
            RuntimeError: If all retry attempts fail
        '''
        retry_attempts = 3
        attempt = 0
        bid_warning = ""
        response = initial_response

        while attempt < retry_attempts:
            try:
                # Print response with clear separator
                print("\n" + "="*70)
                print(f"[Clock] LLM Response (Agent: {agent.name}, Clock: {self.clock+1}, Attempt: {attempt+1})")
                print("="*70)
                print(response)
                print("="*70 + "\n")

                # STEP 1: Parse PLAN using regex
                plan_pattern = r"<PLAN>(.*?)</PLAN>"
                plan_match = re.search(plan_pattern, response, flags=re.IGNORECASE | re.DOTALL)
                if not plan_match:
                    raise ValueError("PLAN tag not found")
                plan = plan_match.group(1).strip()

                # Validate PLAN content
                if len(plan) == 0:
                    raise ValueError("PLAN cannot be empty")

                # STEP 2: Use model-based extraction for ACTION
                action = self.extract_yesno_with_model(response, self.extraction_model)

                print(f"[Clock] Extracted action via model: {action}")

                return plan, action  # Success

            except Exception as e:
                bid_warning = f"\nError: {str(e)}. Please follow the format!"
                print("An error occurred:", e)
                attempt += 1

                if attempt < retry_attempts:
                    # Retry individually for this agent only
                    q_retry = QuestionFreeText(
                        question_name="q_action_retry",
                        question_text=full_prompt + bid_warning
                    )
                    survey_retry = Survey(questions=[q_retry])
                    result_retry = survey_retry.by(self.model).run(cache=self.cache)
                    response = result_retry.select("q_action_retry").to_list()[0]

        raise RuntimeError(f"Failed to process action for {agent.name} after {retry_attempts} attempts")



    def run(self):
        '''Run the clock until the ending condition'''

        # ## elicit agent plans
        # for agent in self.agents:
        #     other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
        #     instruction_str = Prompt.from_txt(os.path.join(prompt_dir,"instruction.txt"))
        #     instruction = str(instruction_str.render({"name":agent.name, "other_agent_names": other_agent_names}))

        #     general_prompt = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" 
        #     if len(agent.reasoning) == 0:
        #         elicit_plan = Prompt.from_txt(os.path.join(prompt_dir,"plan_first.txt"))
        #         prompt_elicit_plan = str(elicit_plan.render({}))

        #         q_plan = QuestionFreeText(
        #             question_name = "q_plan",
        #             question_text = general_prompt +  prompt_elicit_plan
        #         )
        #         survey = Survey(questions = [q_plan])
        #         result = survey.by(self.model).run(cache = self.cache)
        #         plan = result.select("q_plan").to_list()[0]
        #         # plan= result['choices'][0]['message']['content']
        #         print(plan)
        #         agent.reasoning.append(plan)

        #         # stop_condition = False
        #         # while stop_condition is False:
        #         #     self.bid_list = []
        #         #     self.run_one_clock(counterfact = None)
        #         #     print(self.clock+1, '+++++done')
        #         #     self.clock +=1
        #         #     stop_condition = self.declear_winner_and_price()
        #         #     ## calculate the next clock price
        #         #     self.dynamic()
        #         #     print(self.__repr__())

        #     else:
        #         last_round = agent.history[-1]

        #         reflection = Prompt.from_txt(os.path.join(prompt_dir,"reflection.txt"))
        #         prompt_reflection = str(reflection.render({"last_round":last_round}))

        #         q_counterfact = QuestionFreeText(
        #             question_name = "q_counterfact",
        #             question_text = general_prompt+ prompt_reflection
        #         )
        #         result = self.model.simple_ask(q_counterfact)
        #         counterfact= result['choices'][0]['message']['content']
        #         # print("=========================== \n", counterfact)
        #         agent.reflection.append(counterfact)
                
        #         history = agent.history
        #         reasoning = agent.reasoning
        #         max_length = max(len(history), len(reasoning))
        #         history_prompt = ''.join([history[i] +" your plan for this round is: "+ reasoning[i] if i < len(history) and i < len(reasoning) else history[i] if i < len(history) else reasoning[i] for i in range(max_length)])
        #         # previous_plan = agent.reasoning[-1]
        #         elicit_plan = Prompt.from_txt(os.path.join(prompt_dir,"plan_after_reflec.txt"))
        #         prompt_elicit_plan = str(elicit_plan.render({"history": history_prompt, "counterfact":counterfact}))
        #         q_plan = QuestionFreeText(
        #             question_name = "q_plan",
        #             question_text = general_prompt + prompt_elicit_plan
        #         )
        #         # print(q_plan)
        #         # result = self.model.simple_ask(q_plan)
        #         survey = Survey(questions = [q_plan])
        #         result = survey.by(self.model).run(cache = self.cache)
        #         plan = result.select("q_plan").to_list()[0]
        #         # plan= result['choices'][0]['message']['content']
        #         print(plan, "====================\n")
        #         agent.reasoning.append(plan)

        for agent in self.agents:
            agent.reasoning.append("")

        stop_condition = False
        while stop_condition is False:

            self.bid_list = []
            # self.run_one_clock(counterfact = True if self.agents[0].reflection else None)
            self.run_one_clock()
            print(self.clock+1, '+++++done')
            self.clock +=1
            stop_condition = self.declear_winner_and_price()
            ## calculate the next clock price
            self.dynamic()
            print(self.__repr__())
                
        print(self.winner)
        for agent in self.agents:
            if agent.name == self.winner["winner"]:
                agent.profit.append(agent.current_value - float(self.winner["price"]))
                agent.exit_price.append(str(self.winner["price"]))
                agent.winning.append(True)
            else:
                agent.profit.append(0)
                agent.winning.append(False)
        return {'bidding history':self.exit_list, 'winner':self.winner}

    # DEPRECATED: parse_action() has been replaced by parse_plan_and_action_clock()
    # Old method kept for reference but no longer used

    def share_information(self):
        if self.rule.open_blind == "open":
            if self.exit_number == 0:
                return f'In clock period {self.clock+1}, the price was {self.current_price}, no players dropped out'
            else:
                return f'In clock period {self.clock+1}, the price was {self.current_price}, {self.exit_number} players dropped out'
        elif self.rule.open_blind == "blind":
            return ""  # Return empty string instead of None to avoid join() error


    def declear_winner_and_price(self):
        ## The rules for deciding winners
        if self.rule.ascend_descend == "ascend":
            if len(self.agent_left) == 1:
                winner = self.agent_left[0].name
                price = self.current_price
                self.winner = {'winner':winner, 'price':price}
                self.exit_list.append({"agent":winner,"bid": price})
                return True
            elif len(self.agent_left) > 1:
                return False
            elif len(self.agent_left) == 0:
                winners = [self.exit_list[i]["agent"] for i in range(len(self.exit_list)) if self.exit_list[i]["bid"] == self.current_price]
                # randomly choose a winner
                winner = random.choice(winners)
                self.winner = {'winner':winner, 'price':self.current_price}
                return True
        elif self.rule.ascend_descend == "descend":
            if len(self.agent_left) == 1:
                winner = self.agent_left.name
                price = self.current_price
                self.winner = {'winner':winner, 'price':price}
                return True
            elif len(self.agent_left) > 1:
                ## Equal probablity to pick up one gamer
                bidder_i = random.randint(0, len(self.agent_left))
                winner = self.bid_list[bidder_i]['agent']
                return True
            elif len(self.agent_left) == 0:
                return False


class ClockSurvey():
    """
    Parallel survey-based clock auction implementation.

    Instead of running sequential rounds, asks all price points simultaneously
    and determines dropout prices from survey responses.
    """
    def __init__(self, agents, rule, model, cache=None, history=None, extraction_model=None):
        # Basic setup
        self.rule = rule
        self.agents = agents[:]
        self.increment = self.rule.increment
        self.model = model
        self.cache = cache
        self.extraction_model = extraction_model or model
        self.history = history

        # Survey-specific attributes
        self.survey_responses = {}  # (agent_name, price) -> "yes"/"no"
        self.dropout_prices = {}    # agent_name -> lowest dropout price
        self.winner = None

        # For compatibility with existing code
        self.bid_list = []
        self.exit_list = []
        self.transcript = []

    def __repr__(self):
        return f'ClockSurvey Auction: (dropout_prices={self.dropout_prices})'

    def generate_price_points(self, agent):
        """Generate 15 price points centered around agent's value."""
        center = agent.current_value
        increment = self.rule.increment
        min_price = increment  # Minimum price is 1*increment

        prices = []
        for offset in range(-7, 8):  # -7 to +7 = 15 prices
            price = center + (offset * increment)
            if price >= min_price:
                prices.append(price)

        # Ensure we have exactly 15 prices
        # If value is low and we have < 15 prices, add more above the value
        while len(prices) < 15:
            prices.append(prices[-1] + increment)

        return prices

    def build_history_section_clock(self):
        """Build history information string for clock auctions."""
        if not self.history or len(self.history) == 0:
            return ""

        history_lines = ["=== History of Previous Rounds ==="]
        for trans in self.history:
            history_lines.append(str(trans))
        history_lines.append("\n=== Current Round ===")

        return "\n".join(history_lines)

    def build_survey_question(self, agent, price, question_index):
        """Build a single survey question for one agent at one price."""
        # Get instruction and rule explanation (same as Clock class)
        other_agent_names = ', '.join([a.name for a in self.agents if a != agent])
        instruction = Prompt.from_txt(os.path.join(prompt_dir, "instruction.txt"))
        instruction_str = str(instruction.render({
            "name": agent.name,
            "other_agent_names": other_agent_names
        }))

        general_prompt = instruction_str + "\n" + str(self.rule.rule_explanation) + "\n"

        # Render survey template with all needed variables
        survey_template = Prompt.from_txt(os.path.join(prompt_dir, "clock_survey.txt"))
        prompt_content = str(survey_template.render({
            "current_value": agent.current_value,
            "price": price,
            "increment": self.rule.increment
        }))

        full_prompt = general_prompt + prompt_content

        # Sanitize price for question_name (replace decimal point with underscore)
        price_str = str(price).replace('.', '_')
        question_name = f"q_survey_{agent.name.replace(' ', '_')}_price_{price_str}_idx_{question_index}"
        return QuestionFreeText(question_name=question_name, question_text=full_prompt)

    def run_survey(self):
        """Execute parallel survey for all agents at all price points."""
        questions = []
        question_metadata = []
        question_index = 0

        for agent in self.agents:
            prices = self.generate_price_points(agent)

            for price in prices:
                # Build question prompt
                question = self.build_survey_question(agent, price, question_index)
                questions.append(question)

                # Track metadata (sanitize price for question_name)
                price_str = str(price).replace('.', '_')
                question_name = f"q_survey_{agent.name.replace(' ', '_')}_price_{price_str}_idx_{question_index}"
                question_metadata.append({
                    'agent': agent,
                    'price': price,
                    'question_name': question_name,
                    'question_index': question_index
                })
                question_index += 1

        # Execute all in parallel
        print(f"Executing survey with {len(questions)} questions for {len(self.agents)} agents")
        survey = Survey(questions=questions)
        result = survey.by(self.model).run(cache=self.cache)

        return result, question_metadata

    def _parse_plan_and_action(self, response_text):
        """Parse PLAN and ACTION from response text."""
        # Parse PLAN
        plan_pattern = r"<PLAN>(.*?)</PLAN>"
        plan_match = re.search(plan_pattern, response_text, flags=re.IGNORECASE | re.DOTALL)
        if not plan_match:
            raise ValueError("PLAN tag not found")
        plan = plan_match.group(1).strip()

        if len(plan) == 0:
            raise ValueError("PLAN cannot be empty")

        # Parse ACTION using model extraction (same as Clock class)
        action = self.extract_yesno_with_model(response_text)

        return plan, action

    def extract_yesno_with_model(self, full_response_text):
        """Use model to extract yes/no from response."""
        q_extract = QuestionYesNo(
            question_name="extract_yesno",
            question_text=f"""Given the following response from a bidder in a clock auction survey,
determine if they are WILLING TO DROP OUT at this price (Yes) or want to STAY IN (No).

The response may contain an <ACTION> tag with Yes/No, or express the decision
in natural language.

Bidder Response:
{full_response_text}

Is the bidder willing to DROP OUT at this price?"""
        )

        survey = Survey(questions=[q_extract])
        result = survey.by(self.extraction_model).run(cache=self.cache)
        response = result.select("extract_yesno").to_list()[0]

        if isinstance(response, str):
            return response.lower()
        else:
            raise ValueError(f"Invalid extraction result: {response}")

    def parse_survey_responses(self, result, question_metadata):
        """Parse all survey responses and store results with parallel yes/no extraction."""
        # Step 1: Extract all PLANs and responses using regex (fast, no API calls)
        response_data = []
        for metadata in question_metadata:
            agent = metadata['agent']
            price = metadata['price']
            question_name = metadata['question_name']

            response_text = result.select(question_name).to_list()[0]

            # Print response
            print("\n" + "="*70)
            print(f"[Survey] Agent: {agent.name}, Price: ${price}")
            print("="*70)
            print(response_text)
            print("="*70 + "\n")

            # Parse PLAN using regex
            plan_pattern = r"<PLAN>(.*?)</PLAN>"
            plan_match = re.search(plan_pattern, response_text, flags=re.IGNORECASE | re.DOTALL)

            if plan_match:
                plan = plan_match.group(1).strip()
            else:
                print(f"Warning: PLAN tag not found for {agent.name} at ${price}")
                plan = "No plan provided"

            response_data.append({
                'agent': agent,
                'price': price,
                'response_text': response_text,
                'plan': plan,
                'question_name': question_name
            })

        # Step 2: Create parallel yes/no extraction questions for all responses
        extraction_questions = []
        for i, data in enumerate(response_data):
            q_extract = QuestionYesNo(
                question_name=f"extract_yesno_{i}",
                question_text=f"""Given the following response from a bidder in a clock auction survey,
determine if they are WILLING TO DROP OUT at this price (Yes) or want to STAY IN (No).

The response may contain an <ACTION> tag with Yes/No, or express the decision
in natural language.

Bidder Response:
{data['response_text']}

Is the bidder willing to DROP OUT at this price?"""
            )
            extraction_questions.append(q_extract)

        # Step 3: Execute all extractions in parallel
        print(f"Extracting yes/no from {len(extraction_questions)} responses in parallel...")
        extraction_survey = Survey(questions=extraction_questions)
        extraction_result = extraction_survey.by(self.extraction_model).run(cache=self.cache)

        # Step 4: Store all results
        for i, data in enumerate(response_data):
            agent = data['agent']
            price = data['price']
            plan = data['plan']

            # Get extracted yes/no
            try:
                action = extraction_result.select(f"extract_yesno_{i}").to_list()[0]
                if isinstance(action, str):
                    action = action.lower()
                else:
                    raise ValueError(f"Invalid extraction result: {action}")
            except Exception as e:
                print(f"Warning: Error extracting yes/no for {agent.name} at ${price}: {e}")
                action = "no"  # Default to stay in

            # Store response
            key = (agent.name, price)
            self.survey_responses[key] = action

            # Store reasoning
            if not hasattr(agent, 'survey_reasoning'):
                agent.survey_reasoning = {}
            agent.survey_reasoning[price] = plan

            print(f"[Survey] {agent.name} at ${price}: {action}")

    def determine_dropout_prices(self):
        """For each agent, find lowest price where they're willing to drop out."""
        for agent in self.agents:
            prices = sorted(self.generate_price_points(agent))
            dropout_price = None

            # Find first "yes" (willing to drop out)
            for price in prices:
                key = (agent.name, price)
                response = self.survey_responses.get(key, "no")

                if response == "yes":
                    dropout_price = price
                    break

            # Edge case: never drops out
            if dropout_price is None:
                dropout_price = max(prices) + self.rule.increment
                print(f"Warning: {agent.name} never dropped out, using {dropout_price}")

            self.dropout_prices[agent.name] = dropout_price
            agent.exit_price.append(str(dropout_price))

            print(f"{agent.name} dropout price: ${dropout_price}")

    def declare_winner_and_price(self):
        """Determine winner and price based on dropout prices."""
        # Sort agents by dropout price (descending)
        sorted_agents = sorted(
            self.agents,
            key=lambda a: self.dropout_prices[a.name],
            reverse=True
        )

        winner_agent = sorted_agents[0]

        # Price = second-highest dropout price
        if len(sorted_agents) > 1:
            price = self.dropout_prices[sorted_agents[1].name]
        else:
            price = self.dropout_prices[winner_agent.name]

        self.winner = {
            'winner': winner_agent.name,
            'price': price
        }

        # Build exit_list for compatibility
        for agent in sorted_agents:
            self.exit_list.append({
                "agent": agent.name,
                "bid": self.dropout_prices[agent.name]
            })

        print(f"Winner: {winner_agent.name} at price ${price}")

    def attach_reasoning(self):
        """Attach reasoning from dropout price decision to agent."""
        for agent in self.agents:
            dropout_price = self.dropout_prices[agent.name]

            # Get reasoning from the dropout price decision
            if hasattr(agent, 'survey_reasoning') and dropout_price in agent.survey_reasoning:
                reasoning = agent.survey_reasoning[dropout_price]
            else:
                # Fallback: use reasoning from closest price
                if hasattr(agent, 'survey_reasoning') and len(agent.survey_reasoning) > 0:
                    closest_price = min(
                        agent.survey_reasoning.keys(),
                        key=lambda p: abs(p - dropout_price)
                    )
                    reasoning = agent.survey_reasoning[closest_price]
                else:
                    reasoning = "No reasoning available"

            agent.reasoning.append(reasoning)

    def update_agent_profits(self):
        """Update agent profits based on auction outcome."""
        for agent in self.agents:
            if agent.name == self.winner["winner"]:
                profit = agent.current_value - float(self.winner["price"])
                agent.profit.append(profit)
                agent.winning.append(True)
            else:
                agent.profit.append(0)
                agent.winning.append(False)

    def run(self):
        """Main execution method for survey-based clock auction."""
        # Step 1: Execute parallel survey
        result, question_metadata = self.run_survey()

        # Step 2: Parse responses
        self.parse_survey_responses(result, question_metadata)

        # Step 3: Determine dropout prices
        self.determine_dropout_prices()

        # Step 4: Declare winner and price
        self.declare_winner_and_price()

        # Step 5: Attach reasoning
        self.attach_reasoning()

        # Step 6: Update agent profits
        self.update_agent_profits()

        return {'bidding history': self.exit_list, 'winner': self.winner}


class Bidder():
    '''
    This class specifies the agents
    '''
    def __init__(self, value_list, name, rule, common_value_list=[]):
        self.agent = None
        self.rule = rule
        
        self.name = f"Bidder {name}"
        self.value = value_list
        self.current_value = value_list[0]
        self.common_value = common_value_list
        self.current_common = common_value_list[0] if common_value_list is not None else 0
        self.submitted_bids = []
        self.exit_price = []
        self.profit = []
        # self.winner_profit = []
        self.winning = []
        self.history = []
        self.reasoning = []
        self.reflection = []
        
    def __repr__(self):
        return repr(self.agent)

    def build_bidder(self, current_round):
        # value_prompt = f"Your value towards to the prize is {self.value[current_round]}"
        # goal_prompt = "You need to maximize your profits. If you win the bid, your profit is your value for the prize subtracting by your final bid. If you don't win, your profit is 0."
        # goal_prompt = "You need to maximize your overall profit. "
        # history_prompt = ''.join(self.history[:current_round])
        
        agent_traits = {
            # "scenario": self.rule.rule_explanation,
            # "value": value_prompt,
            # "goal": goal_prompt,
            # "history": history_prompt
        }
        self.agent = Agent(name=self.name, traits = agent_traits )
        self.current_value = self.value[current_round]
        self.current_common = self.common_value[current_round]
     
   
class Auction_plan():
    '''
    This class manages the auction process using specified agents and rules.
    '''
    def __init__(self, number_agents, rule, output_dir, timestring=None,cache=None, model='gpt-4o',temperature = 0, service_name=None, extraction_model_name='gpt-4o-mini'):
        self.rule = rule        # Instance of Rule
        self.agents = []  # List of Agent instances
        self.number_agents = number_agents
        self.service_name = service_name
        if service_name:
            self.model= Model(model, temperature=temperature, service_name=service_name)
        else:
            self.model= Model(model, temperature=temperature)
        self.cache = cache
        self.output_dir = output_dir
        self.timestring =timestring
        self.round_number = 0

        # Store extraction model name for later use
        self.extraction_model_name = extraction_model_name

        self.bids = []          # To store bid values
        self.history = []
        self.values_list = []
        self.common_value_list = []
        self.winner_list = []
        self.data_to_save = {}
        
    def draw_value(self, seed=1234):
        '''
        Determine the values for each bidder using a common value and a private part.
        '''
        # make it reproducible
        random.seed(seed)
        # Initialize the values_list as a 2D list
        self.values_list = [[0 for _ in range(self.number_agents)] for _ in range(self.rule.round)]
        
        for i in range(self.rule.round):
            # Generate a common value from a range
            
            if self.rule.private_value == 'private':
                common_value = 0
            elif self.rule.private_value == 'affiliated':
                common_value = random.randint(*self.rule.common_range)
            elif self.rule.private_value == 'common':
                common_value = random.randint(*self.rule.common_range)
            else:
                raise ValueError(f"Rule {self.rule.private_value} not allowed")
            
            self.common_value_list.append(common_value)

            # Generate a private value for each agent and sum it with the common value
            for j in range(self.number_agents):  # Now self.number_agents should be an integer
                
                if self.rule.private_value == 'common':
                    ## if common value auction, the private shock is taken from - private to +private
                    private_part = random.randint(-self.rule.private_range, self.rule.private_range)
                else:
                    private_part = random.randint(0, self.rule.private_range)
                total_value = common_value + private_part
                self.values_list[i][j] = total_value
        print("The values for each bidder are:", self.values_list)

        
    def build_bidders(self):
        '''Instantiate bidders with the value and rule'''
        name_list = ["Andy", "Betty", "Charles", "David", "Ethel", "Florian"]
        for i in range(self.number_agents):
            bidder_values = [self.values_list[round_num][i] for round_num in range(self.rule.round)]
            agent = Bidder(value_list=bidder_values, common_value_list=self.common_value_list, name = name_list[i], rule=self.rule)
            agent.build_bidder(current_round=self.round_number)
            self.agents.append(agent)
 
    def run(self):
        # Simulate the auction process
        # Create extraction model for yes/no distillation in clock auctions
        # Use the same model as the main model to ensure proper service_name configuration
        extraction_model = self.model

        if self.rule.seal_clock == "clock":
            # Check if using survey mode
            use_survey = getattr(self.rule, 'use_survey', False)

            if use_survey:
                auction = ClockSurvey(
                    agents=self.agents,
                    rule=self.rule,
                    cache=self.cache,
                    history=self.history,
                    model=self.model,
                    extraction_model=extraction_model
                )
            else:
                auction = Clock(agents=self.agents, rule=self.rule, cache=self.cache, history=self.history, model=self.model, extraction_model=extraction_model)
            history = auction.run()
        elif self.rule.seal_clock == "seal":
            auction = SealBid(agents=self.agents, rule=self.rule, cache=self.cache, history=self.history, model=self.model)
            history = auction.run()
        else:
            raise ValueError(f"Rule {self.rule.seal_clock} not allowed")
        
        
        self.winner_list.append(history["winner"]["winner"])
        print([agent.profit[self.round_number] for agent in self.agents])
        
        self.data_to_save[f"round_{self.round_number}"] = ({"round":self.round_number, "value":self.values_list[self.round_number],"history":history, "profit":[agent.profit[self.round_number] for agent in self.agents], "common": self.common_value_list[self.round_number], "plan":[agent.reasoning[self.round_number] for agent in self.agents]})
        
    def data_to_json(self):

        print(f"open the file {self.output_dir}, start to write the results")
        print(self.data_to_save)
        save_json(self.data_to_save, f"result_{self.round_number}_{self.timestring}.json", self.output_dir)
        print("Write done!")
        
    def run_repeated(self):
        self.build_bidders()
        while self.round_number < self.rule.round:
            self.run()
            if self.round_number < self.rule.round-1:
                self.update_bidders()
            self.round_number+=1
        self.data_to_json()
            
            
    def update_bidders(self):
        #Following each auction, each subject observes a results summary, containing all submitted bids or exit prices, respectively, her own profit, and the winner’s profit
        print("current bid number", self.round_number)
        if self.rule.seal_clock == "seal":
            bids = [float(agent.submitted_bids[self.round_number]) for agent in self.agents]
            sorted_bids = sorted(bids, reverse=True)
            bid_describe = "All the bids for this round were {}".format(', '.join(map(str, sorted_bids)))
            if self.rule.price_order == "second":
                bid_describe += f". The highest bidder won with a bid of {sorted_bids[0]} and paid {sorted_bids[1]}."
        elif self.rule.seal_clock == "clock":
            bids = [agent.exit_price[self.round_number] for agent in self.agents]
            sorted_bids = sorted(bids, reverse=True)
            bid_describe = "All the exit prices for this round were {}".format(', '.join(map(str, sorted_bids)))


        
        # for agent in self.agents:
        #     if self.rule.seal_clock == "seal":
        #         bid_last_round = agent.submitted_bids[self.round_number]
        #     elif self.rule.seal_clock == "clock":
        #         bid_last_round = agent.exit_price[self.round_number] 
                
        #     value_describe = f"Your value was {agent.current_value}. And you bid {bid_last_round}. "
        #     if self.rule.seal_clock == "seal":
        #         reasoning_describe = f"Your reasoning for your decision was '{agent.reasoning[self.round_number]}' "
        #     else:
        #         reasoning_describe = ""
        #     total = sum(agent.profit[:])
        #     profit_describe = f"Your profit was {agent.profit[self.round_number]} and winner's profit was {winner_profit}. Your total profit is {total} \n"
        #     ## combine into history
        #     description = f"In round {self.round_number}, " + value_describe + profit_describe + reasoning_describe + bid_describe
            
        for agent in self.agents:
            if self.rule.private_value == "private" or self.rule.private_value == "affiliated":
                if self.rule.seal_clock == "seal":
                    bid_last_round = agent.submitted_bids[self.round_number]
                elif self.rule.seal_clock == "clock":
                    bid_last_round = agent.exit_price[self.round_number]
                value_describe = f"Your value was {agent.current_value}, you bid {bid_last_round}, and your profit was {agent.profit[self.round_number]}."
                total = sum(agent.profit[:])
                total_profit_describe = f"Your total profit is {total}. "
                #Combine the personal results and group results
                description = (
                    f"In round {self.round_number}, "
                    + value_describe + "\n"
                    + total_profit_describe + "\n"
                    + bid_describe
                    + f" Did you win the auction: {'Yes' if agent.winning[self.round_number] else 'No'}"
                )
            elif self.rule.private_value == "common":
                if self.rule.seal_clock == "seal":
                    bid_last_round = agent.submitted_bids[self.round_number]
                elif self.rule.seal_clock == "clock":
                    bid_last_round = agent.exit_price[self.round_number]
                value_describe = f"Your (perceived) total value was {agent.current_value}, you bid {bid_last_round}, the (true) common value of the prize was {agent.current_common}, and your profit (based on the true value of the prize) was {agent.profit[self.round_number]}."
                total = sum(agent.profit[:])
                total_profit_describe = f"Your total profit is {total}. "
                #Combine the personal results and group results
                description = (
                    f"In round {self.round_number}, "
                    + value_describe + "\n"
                    + total_profit_describe + "\n"
                    + bid_describe + "\n"
                    + (f"Your reasoning for your decision was '{agent.reasoning[self.round_number]}' " if self.rule.seal_clock == "seal" else "")
                )
            agent.history.append(description)
            # print(agent.history)
            if self.round_number+1 < self.rule.round:
                agent.build_bidder(current_round=self.round_number+1)


        
        
if __name__ == "__main__":
    
    # agents = [
    #     Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds"),
    #     Agent(name = "Robin", instruction = "You are bidder 2, you need to stay for 3 round"),
    #     Agent(name = "Ben", instruction = "You are bidder 3"),
    # ]
    seal_clock='seal'
    ascend_descend=''
    price_order='second'
    private_value='common'
    open_blind='close'
    number_agents=2
    
    rule = Rule_plan(seal_clock=seal_clock, price_order=price_order, private_value=private_value,open_blind=open_blind, rounds=20, common_range=[0, 79], private_range=79, increment=1, number_agents=number_agents)
    rule.describe()
    
    model_list = ["gpt-4-1106-preview", "gpt-4-turbo", "gpt-3.5","gpt-4o"]
    sys.exit()
    # model = Model("gpt-4o", temperature=0)
    
    # q = QuestionFreeText(question_text = dedent("""\
    #     What's your goal?
    #     """), 
    #     question_name = "response"
    # )
    # survey = Survey([q])
    
    # transcript = []
    # s = Scenario({'agent_1_name': agents[0].name, 
    #               'agent_2_name': agents[1].name, 
    #               'transcript': transcript}) 
    # results = survey.by(agents[1]).by(s).run(cache = c)
    # print(results)
    # response = results.select('response').first()
    # print("====", response )
    
    ## Test Sealed bid
    # s = SealBid(agents=agents, rule=rule)
    # s.run()
    # print(s)
    
    # Test clock
    # s = Clock(agents=agents, rule=rule)
    # s.run_one_round()
    # print(s)
    
    ## Test run
    # s.run()
    # print(s)
    
    
    # Test Auction class
    ## Test draw value
    a = Auction(number_agents=3, rule=rule, output_dir=output_dir, timestring=timestring,cache=c, model ='gpt-4o', temperature=0)
    a.draw_value(seed=1456)
    
    ## Test Agent build
    a.build_bidders()
    # print(a.agents)
    
    ## Test on running
    a.run()
    c.write_jsonl("running.jsonl")
    
    ## Test on the descend clock
    #the asking prompt
    
    ## Test for repeated game
    
    ## Test for Scenario
    # what kind of infor to put into the scenatrio
    # what's the difference between putting infor into the question and the scenatio?
    
    ## Test prompt structure
    ## how to input the prompts
    
    # auction = Auction(agents, rule=rule)
