function data = mdp_LipAperture(data, varargin)
%MDP_LIPAPERTURE  - MVIEW dataproc that computes derived signal Lip Aperture (LA)
%
% by default applies to trajectories named "UL" and "LL"
% to use different names specify cellstr varargin as {'<UL>','<LL>'}
%
% appends "LA" signal as DATA(end+1); to specify different name use 3rd argument to varargin{1}
%
% usage examples: 
%
% use default "UL" and "LL"
% mview(...,'DPROC','mdp_LipAperture',...)
%
% use trajectory names "UPPERLIP", "LOWERLIP" with output name "LIPAPER"
% mview(...,'DPROC',{{'mdp_LipAperture',{'UPPERLIP','LOWERLIP','LIPAPER'}}}, ...)
%
% add LA trajectory w/o mview
% data = mdp_LipAperture(data)

% mkt 11/01

LAname = 'LA';
if length(varargin) > 2,	% last arg is {pal,phar,labs}
	traj = upper(varargin(1:end-1));
	if length(traj) > 2, LAname = traj{3}; end;
else,
	traj = {'UL','LL'};
end;
names = upper({data.NAME});
UL = strmatch(traj{1}, names, 'exact');
LL = strmatch(traj{2}, names, 'exact');
if isempty(UL) || isempty(LL),
	error('can''t find %s and %s trajectories in data',traj{:});
end;
if ~isempty(strmatch(LAname,names,'exact')),
	error('%s already exists',LAname);
end;

data(end+1) = data(UL);
data(end).NAME = LAname;
nDims = size(data(LL).SIGNAL,2);
if nDims > 3,
	nDims = 3;
elseif nDims == 3,
	LLz = data(LL).SIGNAL(:,3);
	if range(LLz) < 1 && min(LLz) > 0, nDims = 2; end;	% ignore tilt
end;
data(end).SIGNAL = sqrt(sum((data(UL).SIGNAL(:,1:nDims)-data(LL).SIGNAL(:,1:nDims)).^2,2));
minS = min(data(end).SIGNAL);
maxS = max(data(end).SIGNAL);
spread = maxS - minS;
data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];		% pad
data(end).NCOMPS = 1;
