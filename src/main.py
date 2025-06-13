from edsl.data import Cache
import logging
import os
import pandas as pd
import sys
# from util import Rule, Auction
# from util_human import Auction_human
from util_plan import Auction_plan, Rule_plan
from util_ebay import Auction_ebay
import concurrent.futures

def run_auction(i, human, number_agents, rule, output_dir, c):
    timestring = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    if human:
        ...
        # a = Auction_human(number_agents=number_agents, rule=rule, output_dir=output_dir, timestring=timestring, cache=c, model='gpt-4o', temperature=1)
    elif ebay:
        a = Auction_ebay(number_agents=number_agents, rule=rule, output_dir=output_dir, timestring=timestring, cache=c, model='gpt-4', temperature=0.5)
    else:
        a = Auction_plan(number_agents=number_agents, rule=rule, output_dir=output_dir, timestring=timestring, cache=c, model='gpt-4', temperature=0.5)
    a.draw_value(seed=1401 + i) ## 1399 for affiliated ## 1299 private
    a.run_repeated()
    c.write_jsonl(os.path.join(output_dir, f"raw_output__{timestring}.jsonl"))

if __name__ == "__main__":
    c = Cache()
    
    # Rule Option Menu
    seal_clock = 'seal'
    ascend_descend = 'ascend'
    price_order = 'allpay'
    private_value = 'private'  ### private value / common value / affiliated value
    open_blind = 'open'            ### In AC, whether the information is blind or open
    number_agents = 3
    human = False                  ## Humanistic prompt or not
    ebay = False                    ## If it's eBay auction
    round = 15
    turns = 10
    closing = True
    reserve_price = 60
    
    output_dir = f"experiment_logs/V10/private_all_pay_15"
    # {seal_clock}_{ascend_descend}_{price_order}_{private_value}_{open_blind}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    rule = Rule_plan(
        seal_clock=seal_clock, 
        price_order=price_order, 
        private_value=private_value, 
        open_blind=open_blind, 
        rounds=round, turns=turns , common_range=[20, 79], private_range=99, increment=1, 
        number_agents=number_agents,
        special_name="private_all_pay.txt",
        closing = closing,
        reserve_price = reserve_price)
    rule.describe()

    N = 3 # Repeat for N times

    for i in range(N):
        run_auction( i, human, number_agents, rule, output_dir, c)

    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     futures = [executor.submit(run_auction, i, human, number_agents, rule, output_dir, c) for i in range(N)]

    # for future in concurrent.futures.as_completed(futures):
    #     try:
    #         future.result()
    #     except Exception as e:
    #         print(f"An error occurred: {e}")
