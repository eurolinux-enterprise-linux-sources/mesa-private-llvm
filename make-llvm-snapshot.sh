#!/bin/sh

DIRNAME=llvm-$( date +%Y%m%d )
URL=http://llvm.org/svn/llvm-project/llvm/branches/release_33/
#URL=http://llvm.org/svn/llvm-project/llvm/trunk/

rm -rf $DIRNAME
svn co $URL $DIRNAME |& tail -1 > revision
mv revision $DIRNAME
rm -rf $DIRNAME/.svn

tar Jcf $DIRNAME.tar.xz $DIRNAME
rm -rf $DIRNAME
