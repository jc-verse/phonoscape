function data = mdp_JawAngle(data, varargin)
%MDP_JAWANGLE  - MVIEW dataproc that computes derived signal Jaw Angle (JA)
%
% requires an estimate of head-corrected midsagittal projection of temporomandibular joint (TMJ)
% which can be computed from the mean of the mastoid references with an anterior (~25mm) offset
%
% by default applies to trajectory named "JAW"
% to use different names specify varargin as {TMJ,'<NAME>'}
%
% appends "JA" signal as DATA(end+1); to specify different output name use {TMJ,'<NAME>','<JA_NAME>'}
%
% output in degrees relative to biteplane reference
%
% usage examples: 
%
% use default "JAW" trajectory name and output "JA" name
% mview(...,'DPROC',{{'mdp_JawAngle',{TMJ}}},...)
%
% use trajectory name "MAN" with output name "MANPHI"
% mview(...,'DPROC',{{'mdp_JawAngle',{TMJ,'MAN','MANPHI'}}}, ...)
%
% add JA trajectory w/o mview
% data = mdp_JawAngle(data)

% mkt 04/20

TMJ = varargin{1};

JAname = 'JA';
if length(varargin) > 2,	% last arg is {pal,phar,labs}
	n = upper(varargin(2:end-1));
	JAWname = n{1};
	if length(n) > 1, JAname = n{2}; end;
else,
	JAWname = 'JAW';
end;
names = upper({data.NAME});
JAW = strmatch(JAWname, names, 'exact');
if isempty(JAW),
	error('can''t find %s trajectory in data',JAWname);
end;
if ~isempty(strmatch(JAname,names,'exact')),
	error('%s already exists',JAname);
end;

% compute jaw angle
jaw = data(JAW).SIGNAL;
jaw = jaw(:,1:3) - ones(size(jaw,1),1) * TMJ;
ja = atan2(jaw(:,3),jaw(:,1)) * 180 / pi;

data(end+1) = data(JAW);
data(end).NAME = JAname;
data(end).SIGNAL = ja;
minS = min(data(end).SIGNAL);
maxS = max(data(end).SIGNAL);
spread = maxS - minS;
data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];
data(end).NCOMPS = 1;
