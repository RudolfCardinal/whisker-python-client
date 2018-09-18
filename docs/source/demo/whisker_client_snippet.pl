# Enter a loop to listen to messages from the server.
while (chomp($line = <$MAINSOCK>)) {
    if ($line =~ /^Ping/) {
        # If the server has sent us a Ping, acknowledge it.
        Send("PingAcknowledged");

    } elsif ($line =~ /^Event: (.+)/) {
        # The server has sent us an event.
        $event = $1;

        # Event handling for the behavioural task is dealt with here.

        if ($event =~ /^EndOfTask$/) { last; } # Exit the while loop.
    }
}
