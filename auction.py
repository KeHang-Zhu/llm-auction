from textwrap import dedent
from itertools import cycle

from edsl.data import Cache
from edsl import Agent, Scenario, Survey
from edsl.questions import QuestionFreeText, QuestionYesNo
from util import Rule, Auction


c = Cache()

agents = [
    Agent(name="John", instruction ="you are bidder 1"),
    Agent(name="Robin", instruction="you are bidder 2")
    ]
rule = Rule('open', 'ascending', 'common value')
auction = Auction(agents, rule=rule)
auction.run(n_rounds=10, temperature=0.4)


c.write_jsonl("conversation_cache.jsonl")