# k8sapi2kubectl

One day adventure to make k8s api library to feel more like a kubectl.

The best place to see the usage examples is the [integration_tests.py](https://github.com/Evedel/k8sapi2kubectl/blob/main/tests/integration_tests.py#L14).

If you want to run the code:
1. **DON'T**, it is exploration project only. I'm sane, if you are sane too, please, consider writing `subprocess` wrapper around the `kubectl` binary.

2. Otherwise (most likely won't work out of the box, as all the crd references were `[redacted]`)
```
docker-compose run --rm python run_tests
```

If you want to dev:
```
reopen in devcontainer
```
