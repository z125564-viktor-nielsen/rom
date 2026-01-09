from database import get_ports

ports = get_ports()
for port in ports:
    if "Harkinian" in port['title']:
        print(f"Found port: {port['title']} (ID: {port['id']})")
        print(f"Special Instructions: {port.get('instruction')}")
        print(f"Instruction Text: {port.get('instruction_text')}")
