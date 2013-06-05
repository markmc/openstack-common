# Copyright 2013 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from concurrent import futures
import sys

import tulip

from openstack.common.messaging._executors import base


class TulipExecutor(base.ExecutorBase):

    def __init__(self, conf, listener, callback, event_loop=None):
        super(EventletExecutor, self).__init__(conf, listener, callback)
        self._running = False
        self._task = None
        self._pending_tasks = []
        self._event_loop = event_loop or tulip.get_event_loop()
        self._thread_pool = futures.ThreadPoolExecutor()

    def _execute_callback(self, incoming):
        task = tulip.Task(self.callback(incoming.ctxt, incoming.message))
        incoming.done()

        def callback_done(task):
            try:
                reply = task.result()
                if reply:
                    incoming.reply(reply)
            except Exception:
                incoming.reply(failure=sys.exc_info())
            finally:
                self._pending_tasks.remove(task)

        task.add_done_callback(callback_done)

        self._pending_tasks.append(task)

    @tulip.task
    def _process_async(self, listener):
        while self._running:
            incoming = yield from listener.poll_async()
            self._execute_callback(incoming)

    @tulip.task
    def _process_selectable(self, listener):
        def poll_listener(future):
            incoming = listener.poll(timeout=0)
            if incoming is None:
                return
            self._execute_callback(incoming)
            future.set_result(None)

        while self._running:
            future = tulip.Future()
            poll_listener(future)
            if future.done():
                continue

            self.event_loop.add_reader(listener.fileno(),
                                       poll_listener,
                                       future)
            yield from future

    @tulip.task
    def _process_blocking(self, listener):
        while self._running:
            future = self._event_loop.run_in_executor(self._thread_pool,
                                                      listener.poll)
            self._execute_callback(yield from future)

    def start(self):
        if self._running:
            return
        self._running = True

        if hasattr(self.listener, 'poll_async'):
            m = self._process_async
        elif hasattr(self.listener, 'fileno'):
            m = self._process_selectable
        else:
            m = self._process_blocking

        self._pending_tasks.append(m(listener))

    def stop(self):
        self._running = False
        if hasattr(self.listener, 'fileno'):
            self.event_loop.remove_reader(self.listener.fileno())
        for t in self._pending_tasks:
            t.cancel()
        self._thread_pool.shutdown()

    @tulip.coroutine
    def wait(self):
        yield from tulip.wait(self._pending_tasks)
        self._pending_tasks = []
        self._thread_pool.shutdown(wait=True)
