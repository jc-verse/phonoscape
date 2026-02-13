function t = ExtractTraj(d,ht,tName,comp)
%EXTRACTTRAJ  - extract trajectories over specified intervals
%
%	usage:  t = ExtractTraj(d, ht, tName, comp)
%
% use this procedure to extract intervals of trajectory TNAME from mview-compatible
% array-of-structs variable D as specified by [nIntervals x head,tail] array HT (ms)
% optional trajectory component defaults to 1
%
% returns cell array T {nIntervals}[nSampsx1]

% mkt 01/17

% parse args
if nargin < 3, eval('help ExtractTraj'); return; end;
if nargin < 4 || isempty(comp), comp = 1; end;

% find trajectory index
k = find(strcmp(tName,{d.NAME}));
if isempty(k),
	error('trajectory %s not found in %s', tName, inputname(1));
end;

% convert ms to samples
hts = floor(ht*d(k).SRATE/1000) + 1;

% extract selections
s = d(k).SIGNAL(:,comp);
for ti = 1 : size(ht,1),
	t{ti} = s(hts(ti,1):hts(ti,2));
end;
