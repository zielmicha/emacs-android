#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <sys/ioctl.h>
#include <termios.h>

// fcntl(descr, F_SETFL, O_NONBLOCK)

int forkpty(int* master, void* _pad0, void* _pad1, struct winsize* wsize) {
  // TODO: error checking
  int ptm = open("/dev/ptmx", O_RDWR);
  if(ptm < 0)
    return -1;
  fcntl(ptm, F_SETFD, FD_CLOEXEC);
  grantpt(ptm);
  unlockpt(ptm);
  if(wsize)
    ioctl(ptm, TIOCSWINSZ, wsize);
  char devname[1024];
  ptsname_r(ptm, devname, sizeof(devname));
  int pid;
  if((pid=fork()) == 0) {
    setsid();
    int pts = open(devname, O_RDWR);
    if(pts < 0) return -1;
    dup2(pts, 0);
    dup2(pts, 1);
    dup2(pts, 2);
    close(ptm);
    return 0;
  } else {
    *master = ptm;
    return pid;
  }
}

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
  pid=forkpty(&master, NULL, NULL, &wsize);
  if(pid < 0) {
    perror("forkpty");
    exit(1);
  }
  if(pid != 0) {
    /* TODO: read/write in blocks >1byte */
    while(1) {
      fd_set rfds;
      fd_set wfds;
      fd_set xfds;
      FD_ZERO(&rfds);
      FD_ZERO(&wfds);
      FD_SET(master, &rfds);
      FD_SET(master, &xfds);
      FD_SET(0, &rfds);
      if(select(master + 1, &rfds, &wfds, &xfds, NULL) == -1) {
        perror("select");
        exit(1);
      }
      if(FD_ISSET(0, &rfds)) {
        if(!read(0, buff, 1)) exit(0);
        write(master, buff, 1);
      }
      if(FD_ISSET(master, &rfds)) {
        if(!read(master, buff, 1)) exit(0);
        write(1, buff, 1);
      }
      if(FD_ISSET(master, &xfds)) {
        exit(0);
      }
      int status = 0;

      if(waitpid(-1, &status, WNOHANG) > 0) {
        exit(0);
      }
    }
  } else {
    execvp(argv[1], argv + 1);
  }
}
