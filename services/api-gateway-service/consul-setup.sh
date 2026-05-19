sudo docker run -d \
  --name=consul \
  -p 8500:8500 \
  -p 8600:8600/udp \
  -p 8300:8300 \
  -p 8301:8301 \
  -p 8301:8301/udp \
  -p 8302:8302 \
  -p 8302:8302/udp \
  -e CONSUL_BIND_INTERFACE=eth0 \
  hashicorp/consul:1.16 \
  agent -server -bootstrap-expect=1 -ui -client=0.0.0.0