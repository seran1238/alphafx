STANDARD_PAIRS = {
    frozenset(["EUR", "USD"]): ("EUR", "USD"),
    frozenset(["GBP", "USD"]): ("GBP", "USD"),
    frozenset(["USD", "JPY"]): ("USD", "JPY"),
    frozenset(["USD", "CHF"]): ("USD", "CHF"),
    frozenset(["AUD", "USD"]): ("AUD", "USD"),
    frozenset(["NZD", "USD"]): ("NZD", "USD"),
    frozenset(["USD", "CAD"]): ("USD", "CAD"),
    frozenset(["EUR", "GBP"]): ("EUR", "GBP"),
    frozenset(["EUR", "JPY"]): ("EUR", "JPY"),
    frozenset(["EUR", "CHF"]): ("EUR", "CHF"),
    frozenset(["EUR", "CAD"]): ("EUR", "CAD"),
    frozenset(["EUR", "AUD"]): ("EUR", "AUD"),
    frozenset(["EUR", "NZD"]): ("EUR", "NZD"),
    frozenset(["GBP", "JPY"]): ("GBP", "JPY"),
    frozenset(["GBP", "CHF"]): ("GBP", "CHF"),
    frozenset(["GBP", "CAD"]): ("GBP", "CAD"),
    frozenset(["GBP", "AUD"]): ("GBP", "AUD"),
    frozenset(["GBP", "NZD"]): ("GBP", "NZD"),
    frozenset(["AUD", "JPY"]): ("AUD", "JPY"),
    frozenset(["AUD", "CAD"]): ("AUD", "CAD"),
    frozenset(["AUD", "CHF"]): ("AUD", "CHF"),
    frozenset(["AUD", "NZD"]): ("AUD", "NZD"),
    frozenset(["NZD", "JPY"]): ("NZD", "JPY"),
    frozenset(["NZD", "CHF"]): ("NZD", "CHF"),
    frozenset(["NZD", "CAD"]): ("NZD", "CAD"),
    frozenset(["CAD", "JPY"]): ("CAD", "JPY"),
    frozenset(["CAD", "CHF"]): ("CAD", "CHF"),
    frozenset(["CHF", "JPY"]): ("CHF", "JPY"),
}

def get_trade_direction(strong, weak):
    pair = frozenset([strong, weak])
    if pair in STANDARD_PAIRS:
        base, quote = STANDARD_PAIRS[pair]
        if base == strong:
            return f"LONG {base}/{quote}"
        else:
            return f"SHORT {base}/{quote}"
    return f"LONG {strong}/{weak}"
