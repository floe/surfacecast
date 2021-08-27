# Firewall settings

```
Chain INPUT (policy DROP 405 packets, 44719 bytes)
 pkts bytes target     prot opt in     out     source               destination         
  26M   20G ACCEPT     all  --  lo     any     anywhere             anywhere            
  38M   13G ACCEPT     all  --  any    any     anywhere             anywhere             state RELATED,ESTABLISHED
 3036  135K ACCEPT     tcp  --  any    any     anywhere             anywhere             tcp dpt:http-alt
  730  108K ACCEPT     udp  --  any    any     anywhere             anywhere             udp dpts:50000:65535

Chain OUTPUT (policy DROP 449 packets, 55760 bytes)
 pkts bytes target     prot opt in     out     source               destination         
  26M   20G ACCEPT     all  --  any    lo      anywhere             anywhere            
 251M  351G ACCEPT     all  --  any    any     anywhere             anywhere             state RELATED,ESTABLISHED
 1841  292K ACCEPT     udp  --  any    any     anywhere             anywhere             udp dpts:50000:65535
   24  5244 ACCEPT     udp  --  any    any     anywhere             anywhere             udp dpt:1900
```
