# Bug Report
##  Issue
WSL incorrectly allows two active listeners if they declare SO_REUSEADDR

##  Tested on
  Window Home, build 1803

##  Steps to Reproduce
 1. Create a new AF_INET6 socket, using SOCKET_STREAM and IPPROTO_IP
 1. Set SO_RESUSEADDR option to true
 1. Bind the socket to a port on the local machine
 1. Start listening on the socket
 1. Create a second socket, using the same options
 1. Set SO_RESUSEADDR option to true on the second socket 
 1. Bind the second socket to the same port

Trivial python scripts are provided in this repo to reproduce this issue:
 1. In a terminal run the server script
 1. In a second terminal attempt to run a second version of the server script

##  Native Ubuntu Behaviour
  The second bind is rejected

```shell
    Traceback (most recent call last):
      File "server.py", line 8, in <module>
        s.bind(serverAddr)
      File "/usr/lib/python2.7/socket.py", line 228, in meth
        return getattr(self._sock,name)(*args)
    socket.error: [Errno 98] Address already in use
```

Strace:
```strace
    socket(AF_INET6, SOCK_STREAM, IPPROTO_IP) = 3
    setsockopt(3, SOL_SOCKET, SO_REUSEADDR, [1], 4) = 0
    bind(3, {sa_family=AF_INET6, sin6_port=htons(12345), inet_pton(AF_INET6, "::1", &sin6_addr), sin6_flowinfo=htonl(0), sin6_scope_id=0}, 28) = -1 EADDRINUSE (Address already in use)
```

##  WSL Behaviour
  The second bind is permitted, and is effectively queued behind the first.

Strace:
```strace
    socket(AF_INET6, SOCK_STREAM, IPPROTO_IP) = 3
    setsockopt(3, SOL_SOCKET, SO_REUSEADDR, [1], 4) = 0
    bind(3, {sa_family=AF_INET6, sin6_port=htons(12345), inet_pton(AF_INET6, "::1", &sin6_addr), sin6_flowinfo=htonl(0), sin6_scope_id=0}, 28) = 0
    listen(3, 1)                            = 0
```

##  Expected Behaviour

The behaviour of native ubuntu matches the expected behaviour, as per the man socket(7) page:

```man
	Indicates that the rules used in validating addresses supplied in a bind(2)
	call should allow reuse of local addresses.  For AF_INET sockets this means
	that a socket may bind, except when there is an active listening socket bound
	to the address.  When the listening socket is bound to INADDR_ANY with a
	specific port then it is not possible to bind to this port for any local
	address.  Argument is an integer boolean flag. 
```

With the important section being:
```
	 For AF_INET sockets this means that a socket may bind, **except** when
         there is an active listening socket bound to the address.
```

# Background to the Issue

The issue presents itsself as a hung regression test on a [c++ websockets](https://github.com/Grauniad/CPPWebSocketResponseRequest) server:
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

The NoDoublePortBind regression test is very specific - it verifies the behaviour of the SO_REUSEADDR flag, used by the server when binding to its listening port. The [code](https://github.com/Grauniad/CPPWebSocketResponseRequest/blob/master/src/ReqServer.cpp#L276) this is designed to verify is part of the core server:

```c++
        // Allow address re-use so that orphaned sessions from an old server
        // which are about to be killed off don't prevent us starting up.
        // NOTE: This will *not* allow two active server listeners (see
        //       NoDoublePortBind test)
        requestServer_.set_reuse_addr(true);

        requestServer_.listen(port);

        requestServer_.start_accept();
```

The [regression test](https://github.com/Grauniad/CPPWebSocketResponseRequest/blob/master/test/requestReply.cpp#L276) itself works by attempting to spin up two servers on the same port, verifying that the second server fails:
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
