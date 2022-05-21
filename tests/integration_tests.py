import os
import sys
import logging

from base.k8s_wrapper import (
    InvalidObjectInApply,
    UnrecognizedObjectTypeInApply,
    K8sWrapper,
)

from kubernetes import client


class TestK8sBase:
    def __init__(self, k8s_client: K8sWrapper = K8sWrapper()):
        self.__k8s_client__ = k8s_client
        self.__logger__ = logging.getLogger()

    def test_get_many_kinds(self):
        k: K8sWrapper = self.__k8s_client__

        # cluster-wide resources
        node = k.get(
            k.kind.node, name="ip-xxx-xxx-xxx-xxx.node-name"
        )
        print(f"node by name: {node.metadata.name} ")

        nodes = k.get(k.kind.node)
        print(f"all nodes: {len(nodes.items)} ")

        nodes = k.get(k.kind.node, label_selector="redacted.com/node-pool=high-memory")
        print(f"high mem nodes nodes: {len(nodes.items)} ")

        # namespaced resources
        secret = k.get(k.kind.secret, "redacted-namespace", "svb-test")
        print(f"secret by name: {secret.metadata.namespace} {secret.metadata.name} ")

        secrets = k.get(k.kind.secret, "redacted-namespace")
        print(f"all secrets in rn: {len(secrets.items)} ")

        secrets = k.get(
            k.kind.secret, "redacted-namespace", label_selector="app=svb-app"
        )
        print(f"secrets by selector: {len(secrets.items)} ")

        # crd
        k8s_object = k.get(k.kind.redacted, "redacted-namespace", "redacted-crd-name")
        print(
            f"secret by name: {k8s_object['metadata']['namespace']} {k8s_object['metadata']['name']} {k8s_object['status']['outputs']['version']} "
        )

        k8s_objects = k.get(k.kind.redacted, "redacted-namespace")
        print(f"all redacted crds in rn: {len(k8s_objects['items'])} ")

        return True

    def test_can_apply_get_delete_secrets_from_file_yaml(self):
        k: K8sWrapper = self.__k8s_client__

        k.apply("/workspace/tests/templates/secret.yaml")
        name = k.get(k.kind.secret, "redacted-namespace", "svb-test").metadata.name
        self.__logger__.info(name)
        k.delete(k.kind.secret, "redacted-namespace", "svb-test")

        return True

    def test_can_apply_get_delete_secrets_from_file_json(self):
        k: K8sWrapper = self.__k8s_client__

        k.apply("/workspace/tests/templates/secret.json")
        name = k.get(k.kind.secret, "redacted-namespace", "svb-test").metadata.name
        self.__logger__.info(name)
        k.delete(k.kind.secret, "redacted-namespace", "svb-test")

        return True

    def test_can_apply_get_delete_secrets_from_directory(self):
        k: K8sWrapper = self.__k8s_client__

        k.apply("/workspace/tests/templates/secrets/")

        secrets = k.get(
            k.kind.secret, "redacted-namespace", label_selector="app=svb-test"
        )
        assert len(secrets.items) == 3
        assert secrets.items[0].metadata.name == "svb-test-1"
        assert secrets.items[1].metadata.name == "svb-test-2"
        assert secrets.items[2].metadata.name == "svb-test-3"

        k.delete(k.kind.secret, "redacted-namespace", "svb-test-1")
        k.delete(k.kind.secret, "redacted-namespace", "svb-test-2")
        k.delete(k.kind.secret, "redacted-namespace", "svb-test-3")

        return True

    def test_can_apply_get_delete_secrets_from_k8s_object(self):
        k: K8sWrapper = self.__k8s_client__

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(
                name="svb-test", namespace="redacted-namespace"
            ),
            data={"test": "d29ybGQK"},
        )
        k.apply(secret)
        name = k.get(k.kind.secret, "redacted-namespace", "svb-test").metadata.name
        self.__logger__.info(name)
        k.delete(k.kind.secret, "redacted-namespace", "svb-test")

        return True

    def test_can_apply_get_delete_secrets_from_dictionary(self):
        k: K8sWrapper = self.__k8s_client__

        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=client.V1ObjectMeta(
                name="svb-test", namespace="redacted-namespace"
            ),
            data={"test": "d29ybGQK"},
        )
        secret_dict = secret.to_dict()
        k.apply(secret_dict)
        name = k.get(k.kind.secret, "redacted-namespace", "svb-test").metadata.name
        self.__logger__.info(name)
        k.delete(k.kind.secret, "redacted-namespace", "svb-test")

        return True

    def test_can_apply_get_delete_secrets_from_string_json(self):
        k: K8sWrapper = self.__k8s_client__

        secret = """
{
    "api_version": "v1",
    "data": {"test": "d29ybGQK"},
    "kind": "Secret",
    "metadata": {"name": "svb-test", "namespace": "redacted-namespace"}
}
        """
        k.apply(secret)
        name = k.get(k.kind.secret, "redacted-namespace", "svb-test").metadata.name
        self.__logger__.info(name)
        k.delete(k.kind.secret, "redacted-namespace", "svb-test")

        return True

    def test_can_apply_get_delete_secrets_from_string_yaml(self):
        k: K8sWrapper = self.__k8s_client__

        secret = """
apiVersion: v1
kind: Secret
metadata:
  name: svb-test
  namespace: redacted-namespace
data:
  test: d29ybGQK
        """
        k.apply(secret)
        name = k.get(k.kind.secret, "redacted-namespace", "svb-test").metadata.name
        self.__logger__.info(name)
        k.delete(k.kind.secret, "redacted-namespace", "svb-test")

        return True

    def test_cannot_apply_int(self):
        k: K8sWrapper = self.__k8s_client__

        try:
            k.apply(42)
        except UnrecognizedObjectTypeInApply:
            pass

        return True

    def test_cannot_apply_wrong_str(self):
        k: K8sWrapper = self.__k8s_client__

        try:
            k.apply("i am not a dictionary")
        except InvalidObjectInApply:
            pass

        return True

    def test_cannot_apply_wrong_yaml_str(self):
        k: K8sWrapper = self.__k8s_client__

        try:
            k.apply(
                """
test: i am not a valid yaml
test2
"""
            )
        except InvalidObjectInApply:
            pass

        return True

    def test_cannot_apply_another_wrong_yaml_str(self):
        k: K8sWrapper() = self.__k8s_client__

        try:
            k.apply(
                """
test: i am not a valid yaml
test2:
"""
            )
        except KeyError:
            pass

        return True
