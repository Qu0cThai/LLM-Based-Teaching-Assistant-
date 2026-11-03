import random

def pick(pool, n):
    random.shuffle(pool)
    return pool[:min(len(pool), n)]
