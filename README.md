### Background

The issue presents itsself as a hung regression test on a c++ websockets server:
```
    [==========] Running 8 tests from 1 test case.
    [----------] Global test environment set-up.
    [----------] 8 tests from REQ_CLIENT
    [ RUN      ] REQ_CLIENT.SuccessfulRequest
    [       OK ] REQ_CLIENT.SuccessfulRequest (6 ms)
    [ RUN      ] REQ_CLIENT.RejectedRequest
    [       OK ] REQ_CLIENT.RejectedRequest (3 ms)
    [ RUN      ] REQ_CLIENT.MalformedReject
    [       OK ] REQ_CLIENT.MalformedReject (6 ms)
    [ RUN      ] REQ_CLIENT.InvalidURI
    [       OK ] REQ_CLIENT.InvalidURI (1 ms)
    [ RUN      ] REQ_CLIENT.ServerDown
    [       OK ] REQ_CLIENT.ServerDown (1007 ms)
    [ RUN      ] REQ_CLIENT.AbandonedRequest
    [       OK ] REQ_CLIENT.AbandonedRequest (10 ms)
    [ RUN      ] REQ_CLIENT.InFlightDisconnect
    [       OK ] REQ_CLIENT.InFlightDisconnect (8 ms)
    [ RUN      ] REQ_CLIENT.NoDoublePortBind
 ```

The NoDoublePortBind regression test is very specific - it verifies the behaviour of the SO_REUSEADDR flag, used by the server when binding to its listening port. The code this is designed to verify is part of the core server:

```c++
        // Allow address re-use so that orphaned sessions from an old server
        // which are about to be killed off don't prevent us starting up.
        // NOTE: This will *not* allow two active server listeners (see
        //       NoDoublePortBind test)
        requestServer_.set_reuse_addr(true);

        requestServer_.listen(port);

        requestServer_.start_accept();
```

The regression test itself works by attempting to spin up two servers on the same port, verifying that the second server fails:
```c++
    /**
     * Ensure we can't have two active servers listening on the same port...
     */
    TEST(REQ_CLIENT, NoDoublePortBind)
    {
        WorkerThread serverThread;
        RequestServer server;

        // Request server's main loop is blocking, start up on a slave thread...
        serverThread.PostTask([&] () -> void {
    	    server.AddHandler(EchoSvr::REQUEST_TYPE, EchoSvr::New());
    	    server.HandleRequests(serverPort);
        });
        serverThread.Start();

        server.WaitUntilRunning();

        // Ok, now attempt to spin up a second server. It should be rejected on the
        // grounds of a double port acquisition
        RequestServer duplicate;
        duplicate.AddHandler(EchoSvr::REQUEST_TYPE, EchoSvr::New());
        ASSERT_THROW(
     	    duplicate.HandleRequests(serverPort),
    	    RequestServer::FatalErrorException);
    }

```
