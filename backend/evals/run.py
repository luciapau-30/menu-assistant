"""Run with: python -m evals.run --live --output /tmp/extraction-results.json"""
import argparse
import json
import time
from pathlib import Path


def normalize(value):
    return ' '.join(value.casefold().split())


def measure(expected, actual):
    expected_items = {normalize(i['name']): {normalize(x) for x in i['ingredients']} for i in expected['items']}
    actual_items = {normalize(i['name']): {normalize(x) for x in i['ingredients']} for i in actual['items']}
    expected_pairs = {(name, ingredient) for name, values in expected_items.items() for ingredient in values}
    actual_pairs = {(name, ingredient) for name, values in actual_items.items() for ingredient in values}
    matched = len(expected_pairs & actual_pairs)
    return {
        'exact_match': actual_items == expected_items,
        'ingredient_precision': matched / len(actual_pairs) if actual_pairs else (1.0 if not expected_pairs else 0.0),
        'ingredient_recall': matched / len(expected_pairs) if expected_pairs else 1.0,
        'invented_ingredients': sorted([list(pair) for pair in actual_pairs - expected_pairs]),
        'missing_items': sorted(expected_items.keys() - actual_items.keys()),
        'extra_items': sorted(actual_items.keys() - expected_items.keys()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Send the synthetic fixture images to Groq (uses API quota).')
    parser.add_argument('--predictions', type=Path, help='Offline JSON mapping case IDs to extraction objects.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--delay', type=float, default=0, help='Seconds between live requests to respect provider limits.')
    parser.add_argument('--input-price', type=float, help='USD per million input tokens; supply current provider pricing.')
    parser.add_argument('--output-price', type=float, help='USD per million output tokens.')
    args = parser.parse_args()
    if bool(args.live) == bool(args.predictions):
        parser.error('Choose exactly one of --live or --predictions.')
    from app.llm.vision import PROMPT_VERSION, VISION_MODEL, extract_image
    from app.schemas.extraction import Extraction

    folder = Path(__file__).parent
    cases = json.loads((folder / 'cases.json').read_text())
    predictions = json.loads(args.predictions.read_text()) if args.predictions else {}
    results = []
    for index, case in enumerate(cases):
        if args.live and index and args.delay > 0:
            time.sleep(args.delay)
        start = time.perf_counter()
        metrics = {}
        try:
            actual = (extract_image(str(folder / case['image']), case['type'], metrics=metrics)
                      if args.live else Extraction.model_validate(predictions[case['id']]))
            result = {'id': case['id'], 'valid_output': True, 'prediction': actual.model_dump(),
                      **measure(case['expected'], actual.model_dump())}
        except Exception as exc:
            cause = exc.__cause__
            response = getattr(cause, 'response', None)
            result = {'id': case['id'], 'valid_output': False, 'error_type': type(exc).__name__,
                      'cause_type': type(cause).__name__ if cause else None,
                      'http_status': response.status_code if response is not None else None}
        result['latency_seconds'] = round(time.perf_counter() - start, 3)
        result['usage'] = metrics.get('usage')
        usage = result['usage'] or {}
        result['estimated_cost_usd'] = (
            (usage['prompt_tokens'] * args.input_price + usage['completion_tokens'] * args.output_price) / 1_000_000
            if args.input_price is not None and args.output_price is not None
            and 'prompt_tokens' in usage and 'completion_tokens' in usage else None
        )
        results.append(result)
    output = {'mode': 'live' if args.live else 'offline', 'model': VISION_MODEL,
              'prompt_version': PROMPT_VERSION, 'cases': results,
              'valid_output_rate': sum(r['valid_output'] for r in results) / len(results),
              'exact_match_rate': sum(r.get('exact_match', False) for r in results) / len(results)}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(f"Saved {len(results)} cases to {args.output}; valid output {output['valid_output_rate']:.0%}, exact match {output['exact_match_rate']:.0%}")


if __name__ == '__main__':
    main()
