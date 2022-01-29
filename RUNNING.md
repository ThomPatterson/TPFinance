# Getting the tool up and running

This tool runs uses [Jupyter Notebooks](https://jupyter.org), specifically in the JupyterLab interface.  It uses the [jupyter/scipy-notebook](https://hub.docker.com/r/jupyter/scipy-notebook) docker image to be as portable as possible.  

Steps to get the docker environment running (only tested on macOS).

* make sure docker is running first
* in a terminal from this directory type `make run`

Once up and running the terminal will show output like the following

```
To access the server, open this file in a browser:
        file:///home/jovyan/.local/share/jupyter/runtime/jpserver-8-open.html
    Or copy and paste one of these URLs:
        http://d2bcecdbab1c:8888/lab?token=somelongstring
     or http://127.0.0.1:8888/lab?token=somelongstring
```

Use the last link to open the jupyter runtime instance in your browser.

* Navigate to work > notebooks
