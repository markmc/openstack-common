# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
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

from oslo.config import cfg
from oslo.messaging import notifier

from openstack.common import context


notifier_opts = [
    cfg.StrOpt('default_notification_level',
               default='INFO',
               help='Default notification level for outgoing notifications'),
    cfg.StrOpt('default_publisher_id',
               default='$host',
               help='Default publisher_id for outgoing notifications'),
]

CONF = cfg.CONF
CONF.register_opts(notifier_opts)

_NOTIFIER = None


def _get_notify_func():
    global _NOTIFIER
    if _NOTIFIER is None:
        _NOTIFIER = notifier.Notifier(cfg.CONF, CONF.default_publisher_id)
    return getattr(_NOTIFIER, CONF.default_notification_level.lower())


def notify_decorator(name, fn):
    """Decorator for notify which is used from utils.monkey_patch().

        :param name: name of the function
        :param function: - object of the function
        :returns: function -- decorated function

    """
    def wrapped_func(*args, **kwarg):
        body = {}
        body['args'] = []
        body['kwarg'] = {}
        for arg in args:
            body['args'].append(arg)
        for key in kwarg:
            body['kwarg'][key] = kwarg[key]

        ctxt = context.get_context_from_function_and_args(fn, args, kwarg)
        notify = _get_notify_func()
        notify(ctxt, name, body)
        return fn(*args, **kwarg)
    return wrapped_func
