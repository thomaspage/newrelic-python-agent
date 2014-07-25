import weakref
import traceback

from newrelic.agent import (FunctionTrace, WebTransaction,
    application as application_instance)

def record_exception(transaction, exc_info):
    import tornado.web

    exc = exc_info[0]
    value = exc_info[1]

    if exc is tornado.web.HTTPError:
        if value.status_code == 404:
            return

    transaction.record_exception(*exc_info)

def request_environment(application, request):
    # This creates a WSGI environ dictionary from a Tornado request.

    result = getattr(request, '_nr_request_environ', None)

    if result is not None:
        return result

    # We don't bother if the agent hasn't as yet been registered.

    settings = application.settings

    if not settings:
        return {}

    request._nr_request_environ = result = {}

    result['REQUEST_URI'] = request.uri
    result['QUERY_STRING'] = request.query

    value = request.headers.get('X-NewRelic-ID')
    if value:
        result['HTTP_X_NEWRELIC_ID'] = value

    value = request.headers.get('X-NewRelic-Transaction')
    if value:
        result['HTTP_X_NEWRELIC_TRANSACTION'] = value

    value = request.headers.get('X-Request-Start')
    if value:
        result['HTTP_X_REQUEST_START'] = value

    value = request.headers.get('X-Queue-Start')
    if value:
        result['HTTP_X_QUEUE_START'] = value

    for key in settings.include_environ:
        if key == 'REQUEST_METHOD':
            result[key] = request.method
        elif key == 'HTTP_USER_AGENT':
            value = request.headers.get('User-Agent')
            if value:
                result[key] = value
        elif key == 'HTTP_REFERER':
            value = request.headers.get('Referer')
            if value:
                result[key] = value
        elif key == 'CONTENT_TYPE':
            value = request.headers.get('Content-Type')
            if value:
                result[key] = value
        elif key == 'CONTENT_LENGTH':
            value = request.headers.get('Content-Length')
            if value:
                result[key] = value

    return result

def retrieve_transaction_request(transaction):
    # Retrieves any request already associated with the transaction.

    return getattr(transaction, '_nr_current_request', None)

def retrieve_request_transaction(request):
    # Retrieves any transaction already associated with the request.

    return getattr(request, '_nr_transaction', None)

def initiate_request_monitoring(request):
    # Creates a new transaction and associates it with the request.
    # We always use the default application specified in the agent
    # configuration.

    application = application_instance()

    # We need to fake up a WSGI like environ dictionary with the key
    # bits of information we need.

    environ = request_environment(application, request)

    # We now start recording the actual web transaction. Bail out though
    # if it turns out that recording of transactions is not enabled.

    transaction = WebTransaction(application, environ)

    if not transaction.enabled:
        return

    transaction.__enter__()

    request._nr_transaction = transaction

    request._nr_wait_function_trace = None
    request._nr_request_finished = False

    # We also need to add a reference to the request object in to the
    # transaction object so we can later access it in a deferred. We
    # need to use a weakref to avoid an object cycle which may prevent
    # cleanup of the transaction.

    transaction._nr_current_request = weakref.ref(request)

    return transaction

def suspend_request_monitoring(request, name, group='Python/Tornado',
        terminal=True, rollup='Async Wait'):

    # Suspend the monitoring of the transaction. We do this because
    # we can't rely on thread local data to separate transactions for
    # requests. We thus have to move it out of the way.

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        _logger.error('Runtime instrumentation error. Suspending the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))

        return

    # Create a function trace to track the time while monitoring of
    # this transaction is suspended.

    request._nr_wait_function_trace = FunctionTrace(transaction,
            name=name, group=group, terminal=terminal, rollup=rollup)

    request._nr_wait_function_trace.__enter__()

    transaction.drop_transaction()

def resume_request_monitoring(request, required=False):
    # Resume the monitoring of the transaction. This is moving the
    # transaction stored against the request as the active one.

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        if not required:
            return

        _logger.error('Runtime instrumentation error. Resuming the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))

        return

    # Now make the transaction stored against the request the current
    # transaction.

    transaction.save_transaction()

    # Close out any active function trace used to track the time while
    # monitoring of the transaction was suspended. Technically there
    # should always be an active function trace but check and ignore
    # it if there isn't for now.

    try:
        if request._nr_wait_function_trace:
            request._nr_wait_function_trace.__exit__(None, None, None)

    finally:
        request._nr_wait_function_trace = None

    return transaction

def finalize_request_monitoring(request, exc=None, value=None, tb=None):
    # Finalize monitoring of the transaction.

    transaction = retrieve_request_transaction(request)

    if transaction is None:
        _logger.error('Runtime instrumentation error. Finalizing the '
                'Tornado transaction but there was no transaction cached '
                'against the request object. Report this issue to New Relic '
                'support.\n%s', ''.join(traceback.format_stack()[:-1]))

        return

    # If all nodes hadn't been popped from the transaction stack then
    # error messages will be logged by the transaction. We therefore do
    # not need to check here.

    transaction.__exit__(exc, value, tb)

    request._nr_transaction = None
    request._nr_wait_function_trace = None
    request._nr_request_finished = True
