def count_sentiments(rows):
    result = {}
    for r in rows:
        result[r] = result.get(r, 0) + 1
    return result
