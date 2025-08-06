from collections import Counter

"""
Not used as logic for project, alternate approach not using poker libraries
"""
def hand_rank(cards):
    """
    reference:
    8 = Straight flush
    7 = Four of a kind
    6 = Full house
    5 = Flush
    4 = Straight
    3 = Three of a kind
    2 = Two pair
    1 = One pair
    0 = High card
    """
    card_dict = {
    "A": 14,
    "K": 13,
    "Q": 12,
    "J": 11,
    "T": 10,
    "9": 9,
    "8": 8,
    "7": 7,
    "6": 6,
    "5": 5,
    "4": 4,
    "3": 3,
    "2": 2,
    "h": 1,
    "d": 2,
    "s": 3,
    "c": 4
}
    Output = []
    card_list = [0] * 7
    for index, card in enumerate(cards):
        card_list[index] = card_dict[card[0]]*10 + card_dict[card[1]]
    card_list.sort()
    card_list.reverse()

    rank_list = [x//10 for x in card_list]
    suit_list = [x%10 for x in card_list]

    #Find Quads - no chance for straight/flush
    rank_dict = Counter(rank_list)
    for key, value in rank_dict.items():
        if value == 4:
            Output.append(7)
            Output.append(key)
            for x in rank_list:
                if x!= key:
                    Output.append(x)
                    return tuple(Output)
                


result = hand_rank(['As', 'Ad', 'Ac', 'Ah', '9s', 'Jh', '7d'])
print(result)