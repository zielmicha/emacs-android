#include <pty.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>

// fcntl(descr, F_SETFL, O_NONBLOCK)

int main(int argc, char** argv) {
  if(argc < 2) {
    fprintf(stderr, "Usage: ROWS=n COLS=n ./pty-helper program [args...]\n");
    exit(1);
  }
  int pid;
  int master;
  char buff[1];
  struct winsize wsize;
  wsize.ws_row = atoi(getenv("ROWS"));
  wsize.ws_col = atoi(getenv("COLS"));
  if((pid=forkpty(&master, NULL, NULL, &wsize))) {
    /* TODO: read/write in blocks >1byte */
    while(1) {
      fd_set rfds;
      fd_set wfds;
      FD_ZERO(&rfds);
      FD_ZERO(&wfds);
      FD_SET(master, &rfds);
      //FD_SET(master, &wfds);
      FD_SET(0, &rfds);
      //FD_SET(1, &wfds);
      select(master + 1, &rfds, &wfds, NULL, NULL);
      if(FD_ISSET(0, &rfds)) {
        if(!read(0, buff, 1)) exit(3);
        write(master, buff, 1);
      }
      if(FD_ISSET(master, &rfds)) {
        if(!read(master, buff, 1)) exit(2);
        write(1, buff, 1);
      }
    }
  } else {
    execvp(argv[1], argv + 1);
  }
}
