def unique_seq(seq, criteria):
    seen = []
    for item in seq:
        if criteria(item) not in seen:
            seen.append(criteria(item))
            yield item

def distinct(seq, criteria = lambda x: x, cast=list):
    ''' Returns sequence with distincs values keeping order '''
    return cast(unique_seq(seq, criteria))