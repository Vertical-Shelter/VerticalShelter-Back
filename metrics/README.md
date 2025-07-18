# Metrics

## deployment

```bash	
scp -r metrics/ ec2-user@ec2-3-253-247-153.eu-west-1.compute.amazonaws.com:~/.
```

## run

```bash
ssh ec2-user@ec2-3-253-247-153.eu-west-1.compute.amazonaws.com
cd metrics
docker-compose -f metrics-docker-compose.yaml up --build -d
```

