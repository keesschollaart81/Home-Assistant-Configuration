find /share/motion/front-door/*.* -mtime +4 -exec rm {} \; 
find /backup/* -mtime +90 -exec rm {} \;