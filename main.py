from edsl.data import Cache

from util import Rule, Auction


if __name__ == "__main__":
    c = Cache()
    
    #Rule Option Menu for Anand
    # seal_clock= 'seal' or 'clock' 
    # ascend_descend='ascend' or 'descend' if seal_clock= 'clock' 
    # price_order='first' or 'second' or 'third' if seal_clock= 'seal'
    # private_value='private' or 'common'
    # open_blind='open' or 'blind' if seal_clock= 'clock' 
            #i.e. bidder don't see the drop out in the clock

    rule = Rule(seal_clock='seal', ascend_descend='ascend',price_order='first', private_value='private',open_blind='open')
    rule.describe()

    auction = Auction(number_agents=3, rule=rule)
    auction.run(temperature=0.4)

    c.write_jsonl("conversation_cache.jsonl")