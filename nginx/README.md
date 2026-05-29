
if choosing this nginx server as an edge proxy it handles incoming traffic via port(80/443)
Clarify
Does it need routing logic or just config files?? If this does routing does it route to api gateway or will it talk directly to available backend services??
Can we handle load balancing here or api gateway??
Finalize one approach and go from there 
Finally wire it as a single internet facing gateway and modify the docker-compose.yml configuration appropriately