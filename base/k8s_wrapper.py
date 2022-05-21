import json
import os
import yaml

from logging import Logger, getLogger
from kubernetes import client, config

from base.k8s_api_finder import K8sApiFinder


class UnrecognizedObjectTypeInApply(Exception):
    pass


class InvalidObjectInApply(Exception):
    pass


class K8sWrapper:
    class kind:
        secret = "secret"
        pod = "pod"
        deployment = "deployment"
        cron_job = "cron_job"
        config_map = "config_map"
        node = "node"

        redacted = "redacted"

    def __init__(
        self, k8s_client=client, logger: Logger = getLogger(), api_table=K8sApiFinder()
    ):
        config.load_kube_config()
        self.__client__ = k8s_client
        self.__logger__ = logger
        self.__api_table__ = api_table

    def __read_yaml_file_to_dict__(self, path: str) -> dict:
        with open(path) as file:
            return yaml.load(file, Loader=yaml.FullLoader)

    def __read_yaml_str_to_dict__(self, string: str) -> dict:
        return yaml.safe_load(string)

    def __read_json_file_to_dict__(self, path: str) -> dict:
        with open(path) as file:
            return json.load(file)

    def __read_json_str_to_dict__(self, string: str) -> dict:
        return json.loads(string)

    def __read_file_to_dict__(self, path: str) -> dict:
        try:
            return self.__read_yaml_file_to_dict__(path)
        except yaml.YAMLError:
            pass
        try:
            return self.__read_json_file_to_dict__(path)
        except json.JSONDecodeError:
            pass
        raise InvalidObjectInApply(f"{path} is not a valid yaml or json file")

    def __read_string_to_dict__(self, string: str) -> dict:
        # if it is not a valid yaml file,
        # yaml library return the input string
        # without raising an exception
        try:
            loaded_string = yaml.safe_load(string)
            if type(loaded_string) == dict:
                return loaded_string
        except yaml.scanner.ScannerError:
            pass
        try:
            return self.__read_json_str_to_dict__(string)
        except json.JSONDecodeError:
            pass
        raise InvalidObjectInApply(f"Not a valid yaml or json string:\n {string}")



    def __invoke__(self, api, *args, **kwargs):
        self.__logger__.debug(f"Invoking {api} with args {args} and {kwargs}")
        return api(*args, **kwargs)

    def __form_get_args__(self, kind, namespace, name, is_namespaced):
        if self.__api_table__.is_crd(kind):
            crd_def = self.__api_table__.find_crd_definition(kind)
            args = [crd_def["group"], crd_def["version"]]
            if is_namespaced:
                args += [namespace]
            args += [crd_def["plural"], name]
        else:
            args = [name]
            if is_namespaced:
                args = [name, namespace]
        return args

    def __get__(self, kind: str, namespace: str, name: str, **kwargs):
        is_namespaced = False
        if namespace:
            is_namespaced = True

        args = self.__form_get_args__(kind, namespace, name, is_namespaced)
        function = self.__api_table__.find_function("read", kind, is_namespaced)
        try:
            return self.__invoke__(function, *args, **kwargs)
        except client.ApiException as e:
            if e.reason == "Not Found":
                return None
            raise e

    def __form_list_args__(self, kind, namespace, is_namespaced):
        if self.__api_table__.is_crd(kind):
            crd_def = self.__api_table__.find_crd_definition(kind)
            args = [crd_def["group"], crd_def["version"]]
            if is_namespaced:
                args += [namespace]
            args += [crd_def["plural"]]
        else:
            args = []
            if is_namespaced:
                args = [namespace]

        return args

    def __list__(self, kind: str, namespace: str, **kwargs):
        is_namespaced = False
        if namespace:
            is_namespaced = True

        args = self.__form_list_args__(kind, namespace, is_namespaced)
        function = self.__api_table__.find_function("list", kind, is_namespaced)
        try:
            return self.__invoke__(function, *args, **kwargs)
        except client.ApiException as e:
            if e.reason == "Not Found":
                return None
            raise e

    def __delete__(self, kind, namespace, name, **kwargs):
        function = self.__api_table__.find_function("delete", kind)

        try:
            self.__invoke__(function, name, namespace, **kwargs)
        except client.ApiException as e:
            if e.reason == "Not Found":
                return None
            raise e

    def __form_create_args__(self, body, is_namespaced):
        if self.__api_table__.is_crd(body["kind"]):
            crd_def = self.__api_table__.find_crd_definition(body["kind"])
            args = [crd_def["group"], crd_def["version"]]
            if is_namespaced:
                args += [body["metadata"]["namespace"]]
            args += [crd_def["plural"], body]
        else:
            if is_namespaced:
                args = [body["metadata"]["namespace"], body]
            else:
                args = [body]
        return args

    def __form_replace_args__(self, body, is_namespaced):
        if self.__api_table__.is_crd(body["kind"]):
            crd_def = self.__api_table__.find_crd_definition(body["kind"])
            args = [crd_def["group"], crd_def["version"]]
            if is_namespaced:
                args += [body["metadata"]["namespace"]]
            args += [crd_def["plural"], body["metadata"]["name"], body]
        else:
            args = [body["metadata"]["name"]]
            if is_namespaced:
                args += [body["metadata"]["namespace"]]
            args += [body]
        return args

    def __add_resource_version_before_update__(self, body):
        namespace = None
        is_namespaced = True
        try:
            namespace = body["metadata"]["namespace"]
        except KeyError:
            is_namespaced = False

        args = self.__form_get_args__(
            body["kind"], namespace, body["metadata"]["name"], is_namespaced
        )
        read = self.__api_table__.find_function("read", body["kind"], is_namespaced)
        resource = self.__invoke__(read, *args)
        if type(resource) != dict:
            resource = resource.to_dict()
        if ("metadata" in resource) and ("resourceVersion" in resource["metadata"]):
            body["metadata"]["resourceVersion"] = resource["metadata"][
                "resourceVersion"
            ]
        return body

    def __apply__(self, body, **kwargs):
        namespace = None
        is_namespaced = True
        try:
            namespace = body["metadata"]["namespace"]
        except KeyError:
            is_namespaced = False

        try:
            args = self.__form_create_args__(body, is_namespaced)
            function = self.__api_table__.find_function(
                "create", body["kind"], is_namespaced
            )
            self.__invoke__(function, *args, **kwargs)
            self.__logger__.info(
                f"Created {body['kind']} {body['metadata']['name']} in {namespace}"
            )
        except client.ApiException as e:
            if e.body.find('"reason":"AlreadyExists"') != -1:
                body = self.__add_resource_version_before_update__(body)
                args = self.__form_replace_args__(body, is_namespaced)
                function = self.__api_table__.find_function(
                    "replace", body["kind"], is_namespaced
                )
                self.__invoke__(function, *args, **kwargs)
                self.__logger__.info(
                    f"Updated {body['kind']} {body['metadata']['name']} in {body['metadata']['namespace']}"
                )
                return
            raise e

    def get(self, kind, namespace=None, name=None, **kwargs):
        if name:
            return self.__get__(kind, namespace, name, **kwargs)
        else:
            return self.__list__(kind, namespace, **kwargs)

    def delete(self, kind, namespace, name, **kwargs):
        return self.__delete__(kind, namespace, name, **kwargs)

    def apply(self, target, **kwargs):
        if type(target) == str:
            if os.path.isdir(target):
                for root, dirs, files in os.walk(target):
                    for filename in files:
                        manifest = self.__read_file_to_dict__(
                            os.path.join(root, filename)
                        )
                        self.__apply__(manifest, **kwargs)
            elif os.path.isfile(target):
                manifest = self.__read_file_to_dict__(target)
                self.__apply__(manifest, **kwargs)
            else:
                manifest = self.__read_string_to_dict__(target)
                self.__apply__(manifest, **kwargs)
        else:
            if type(target) == dict:
                self.__apply__(target, **kwargs)
            else:
                try:
                    self.__apply__(target.to_dict(), **kwargs)
                except AttributeError:
                    raise UnrecognizedObjectTypeInApply(
                        f"Unrecognised object {type(target)} ::: {target}"
                    )
