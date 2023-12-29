import sys
import os
from garmin_fit_sdk import Decoder, Stream
import json

def convert_fit_to_json(fit_file_path, output_json_path):
    # Load the .fit file
    stream = Stream.from_file(fit_file_path)
    decoder = Decoder(stream)

    # Decode the FIT file
    messages, errors = decoder.read()

    # Handle any errors during decoding
    if errors:
        print("Errors encountered:", errors)
        return

    # Convert the decoded data to JSON format
    json_data = json.dumps(messages, default=str)

    # Save the JSON data to a file
    with open(output_json_path, 'w') as json_file:
        json.dump(messages, json_file, default=str)

    print(f"Conversion complete. JSON data saved to '{output_json_path}'.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python fit_json.py <path_to_fit_file>")
        sys.exit(1)

    fit_file_path = sys.argv[1]  # First command line argument
    base_name = os.path.splitext(fit_file_path)[0]
    output_json_path = base_name + ".json"  # Output JSON file with same base name

    convert_fit_to_json(fit_file_path, output_json_path)

if __name__ == "__main__":
    main()
