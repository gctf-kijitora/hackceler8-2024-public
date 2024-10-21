#!/usr/bin/env python
import server
def main():
  server.MAX_TPS = 3000.0
  server.main()

if __name__ == "__main__":
  main()
