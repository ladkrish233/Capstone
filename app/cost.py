INPUT_PRICE = 0.10  # dollars per 1 million input tokens


OUTPUT_PRICE = 0.50  # dollars per 1 million output tokens


def run_cost(usage) -> float:
    input_cost = usage.input_tokens / 1_000_000 * INPUT_PRICE
    output_cost = usage.output_tokens / 1_000_000 * OUTPUT_PRICE
    return input_cost + output_cost
