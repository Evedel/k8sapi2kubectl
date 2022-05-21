FROM python:3.10-bullseye as python
RUN pip install kubernetes==23.3.0
ENTRYPOINT ["python"]
