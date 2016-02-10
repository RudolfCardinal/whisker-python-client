def test_whisker(server="localhost", port=3233):

    class MyWhiskerTask(WhiskerTask):

        def __init__(self, ):
            super(MyWhiskerTask, self).__init__()  # call base class init
            # ... anything extra here

        def fully_connected(self):
            print("SENDING SOME TEST/DEMONSTRATION COMMANDS")
            self.command("Timestamps on")
            self.command("ReportName WHISKER_CLIENT_PROTOTYPE")
            self.send("TestNetworkLatency")
            self.command("TimerSetEvent 1000 9 TimerFired")
            self.command("TimerSetEvent 12000 0 EndOfTask")

        def incoming_event(self, event, timestamp=None):
            print("Event: {e} (timestamp {t})".format(e=event, t=timestamp))
            if event == "EndOfTask":
                reactor.stop()

    w = MyWhiskerTask()
    w.connect(server, port)
    reactor.run()
