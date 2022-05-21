from kubernetes import client


class K8sApiFinder:
    __KIND_TO_API__ = {
        "pod": "CoreV1Api",
        "secret": "CoreV1Api",
        "config_map": "CoreV1Api",
        "node": "CoreV1Api",
        "deployment": "AppsV1Api",
        "cron_job": "BatchV1beta1Api",

        "redacted": "CustomObjectsApi",
    }

    __CRD_DEFINITION__ = {
        "redacted": {
            "group": "redacted.redacted.com",
            "version": "v1",
            "plural": "redacteds",
        }
    }

    def __init__(self, client=client):
        self.__client__ = client

    def is_defined(self, kind):
        return kind.lower() in self.__KIND_TO_API__

    def is_crd(self, kind):
        kind_lower = kind.lower()
        return kind_lower in self.__CRD_DEFINITION__

    def find_function(self, verb, kind, is_namespaced=True):
        kind_string = kind.lower()
        api_string = self.__KIND_TO_API__[kind_string]
        api = getattr(self.__client__, api_string)()

        function_string = ""

        if is_namespaced:
            function_string = f"{verb}_namespaced_{kind_string}"
        else:
            function_string = f"{verb}_{kind_string}"

        if self.is_crd(kind):
            if verb == "read": verb = "get"
            if is_namespaced:
                function_string = f"{verb}_namespaced_custom_object"
            else:
                function_string = f"{verb}_cluster_custom_object"

        function = getattr(api, function_string)
        return function

    def find_crd_definition(self, kind):
        kind_lower = kind.lower()
        return self.__CRD_DEFINITION__[kind_lower]
