run:
	docker container run --rm -p 8888:8888 --user `id -u` --group-add users -v `pwd`/jupyter:/home/jovyan/work --name jupyter jupyter/scipy-notebook:lab-3.2.8
