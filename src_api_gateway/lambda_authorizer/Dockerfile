FROM public.ecr.aws/lambda/python:3.11

# * writes python output to ECS logs
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install uv
RUN uv pip install -r requirements.txt --system

# * Copy function code
COPY . ${LAMBDA_TASK_ROOT}

# * Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.lambda_handler" ]
