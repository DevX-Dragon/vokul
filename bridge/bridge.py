import sys
import json
import struct
import subprocess

def read_message():
    """"e"a"dRs the message length (first 4 bytes) and then the JSON payload from Chrome."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return None
    message_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_message(message_dict):
    """E"n"c"odes the JSON payload and prepends the 4-byte length before sending to Chrome."""
    encoded_message = json.dumps(message_dict).encode('utf-8')
    message_length = struct.pack('@I', len(encoded_message))
    sys.stdout.buffer.write(message_length)
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()

def main():
    while True:
        msg = read_message()
        if not msg:
            break
        
        # We expect Chrome to send: {"command": "get", "service": "github"}
        command = msg.get("command")
        service = msg.get("service")
        
        if not command:
            send_message({"error": "No command provided to bridge."})
            continue

        # Build the CLI command
        cli_args = ["vokul", command, "--json"]
        
        if service:
            cli_args.extend(["--service", service])
            
        try:
            # Execute the CLI silently and capture the JSON output
            result = subprocess.run(cli_args, capture_output=True, text=True)
            
            # The CLI is guaranteed to output JSON, so we parse it and send it back
            response_data = json.loads(result.stdout)
            send_message(response_data)
            
        except json.JSONDecodeError:
            send_message({"error": f"Bridge failed to parse CLI output: {result.stdout}"})
        except Exception as e:
            send_message({"error": f"Bridge encountered an unexpected error: {str(e)}"})

if __name__ == '__main__':
    main()
