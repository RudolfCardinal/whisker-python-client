# ...
for line in w.getlines_mainsock():
    if options.verbosenetwork:
        print("SERVER: " + line)  # For info only.
    if line == "Ping":
        # If the server has sent us a Ping, acknowledge it.
        w.send("PingAcknowledged")
    if line[:7] == "Event: ":
        # The server has sent us an event.
        event = line[7:]
        if options.verbosenetwork:
            print("EVENT RECEIVED: " + event)  # For info only.
        # Event handling for the behavioural task is dealt with here.
        if event == "EndOfTask":
            break  # Exit the while loop.
