# Pathops

```{toctree}
:maxdepth: 3
:hidden: false

reference/index
```

Pathops is a Python library providing a pathlib-like interface for Juju Kubernetes Charms to interact with files in their workload container.
Interaction with remote files is performed via ContainerPath objects.
A PathProtocol class is provided for use with type annotations, and a LocalPath class is provided which implements PathProtocol for local files.

For more information, see the [charmlibs-pathops repository](https://github.com/canonical/charmlibs-pathops).
