import mido
import time
import sys
from argparse import ArgumentParser


def list_ports():
    """List all available MIDI input and output ports."""
    inputs = mido.get_input_names()
    outputs = mido.get_output_names()

    print("\n=== MIDI Input Ports ===")
    if inputs:
        for i, name in enumerate(inputs, 1):
            print(f"  {i}. {name}")
    else:
        print("  (none found)")

    print("\n=== MIDI Output Ports ===")
    if outputs:
        for i, name in enumerate(outputs, 1):
            print(f"  {i}. {name}")
    else:
        print("  (none found)")
    print()


def resolve_port_name(partial: str, available: list[str]) -> str | None:
    """Find a port by partial name match."""
    for name in available:
        if partial.lower() in name.lower():
            return name
    return None


def listen_ports(port_names: list[str]):
    """Listen to specified MIDI input ports and print messages."""
    available = mido.get_input_names()
    
    resolved_ports: list[str] = []
    for partial in port_names:
        match = resolve_port_name(partial, available)
        if match:
            resolved_ports.append(match)
            print(f"Resolved '{partial}' -> '{match}'")
        else:
            print(f"Warning: No port matching '{partial}' found")
            print(f"Available ports: {', '.join(available)}")

    if not resolved_ports:
        print("No valid ports to listen to.")
        return

    print(f"\nListening on {len(resolved_ports)} port(s). Press Ctrl+C to stop.\n")
    print("-" * 60)

    ports = []
    try:
        for name in resolved_ports:
            port = mido.open_input(name)
            ports.append((name, port))
            print(f"Opened: {name}")
        
        print("-" * 60)
        print("Activity check every 2 seconds. Try disconnecting/reconnecting.")
        print("-" * 60)
        print()

        last_check = time.time()
        check_interval = 2.0
        port_was_available = {name: True for name, _ in ports}
        message_count = {name: 0 for name, _ in ports}

        while True:
            # Process messages
            for name, port in ports:
                for msg in port.iter_pending():
                    timestamp = time.strftime("%H:%M:%S")
                    short_name = name.split()[0] if ' ' in name else name[:20]
                    message_count[name] += 1
                    print(f"[{timestamp}] {short_name:<20} | {msg}")
            
            # Periodic availability check
            now = time.time()
            if now - last_check >= check_interval:
                last_check = now
                current_inputs = mido.get_input_names()
                timestamp = time.strftime("%H:%M:%S")
                
                for name, port in ports:
                    is_available = name in current_inputs
                    was_available = port_was_available[name]
                    
                    if was_available and not is_available:
                        print(f"[{timestamp}] !! PORT DISAPPEARED: {name}")
                        print(f"[{timestamp}]    port.closed = {port.closed}")
                        print(f"[{timestamp}]    Messages received so far: {message_count[name]}")
                    elif not was_available and is_available:
                        print(f"[{timestamp}] !! PORT REAPPEARED: {name}")
                        print(f"[{timestamp}]    port.closed = {port.closed}")
                        print(f"[{timestamp}]    Will messages resume? Keep playing...")
                    
                    port_was_available[name] = is_available
                
                # Show current state
                status = []
                for name, _ in ports:
                    avail = "OK" if port_was_available[name] else "GONE"
                    status.append(f"{name.split()[0][:10]}:{avail}")
                print(f"[{timestamp}] Status: {', '.join(status)} | Available ports: {len(current_inputs)}")
            
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        for name, port in ports:
            port.close()
            print(f"Closed: {name}")


def main():
    parser = ArgumentParser(
        prog="meh-debug",
        description="MIDI Event Handler debug tool for inspecting MIDI ports"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    subparsers.add_parser("list", help="List all available MIDI ports")

    # Listen command
    listen_parser = subparsers.add_parser("listen", help="Listen to MIDI input ports")
    listen_parser.add_argument(
        "ports",
        nargs="+",
        help="Port names (or partial matches) to listen on"
    )

    args = parser.parse_args()

    if args.command == "list":
        list_ports()
    elif args.command == "listen":
        listen_ports(args.ports)


if __name__ == "__main__":
    main()
