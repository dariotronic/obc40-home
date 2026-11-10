/*
 * faccessat-fix: shim LD_PRELOAD per il kernel 4.14 della OBC40.
 *
 * musl recente implementa faccessat() con flag usando la syscall faccessat2
 * (kernel >= 5.8). Sul 4.14 riceve ENOSYS e, se i flag contengono
 * AT_SYMLINK_NOFOLLOW, restituisce EINVAL. GLib usa proprio quel flag in
 * g_file_query_exists(), quindi ogni controllo di esistenza fallisce
 * (es. xfce4-settings-manager vuoto).
 *
 * Qui si prova prima faccessat2; se manca, si emula:
 *  - F_OK + AT_SYMLINK_NOFOLLOW  -> fstatat(..., AT_SYMLINK_NOFOLLOW)
 *  - altri casi: si tolgono i flag emulabili e si usa la faccessat classica.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

int faccessat(int fd, const char *path, int mode, int flag)
{
    if (flag == 0)
        return (int)syscall(SYS_faccessat, fd, path, mode);

    long r = syscall(SYS_faccessat2, fd, path, mode, flag);
    if (r == 0 || errno != ENOSYS)
        return (int)r;

    if (flag & AT_SYMLINK_NOFOLLOW) {
        if (mode == F_OK) {
            struct stat st;
            return fstatat(fd, path, &st, AT_SYMLINK_NOFOLLOW | (flag & AT_EMPTY_PATH));
        }
        flag &= ~AT_SYMLINK_NOFOLLOW;
    }
    if (flag & AT_EACCESS) {
        if (getuid() == geteuid() && getgid() == getegid())
            flag &= ~AT_EACCESS;
    }
    if (flag) {
        errno = EINVAL;
        return -1;
    }
    return (int)syscall(SYS_faccessat, fd, path, mode);
}
